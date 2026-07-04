# Copyright (c) 2026, Administrator and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class LiteTransaction(Document):
    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------
    def validate(self):
        self._validate_allocated_amounts()

    def _validate_allocated_amounts(self):
        """Ensure total allocated amounts do not exceed the paid amount."""
        if self.has_party and self.allocations:
            total_allocated = sum(flt(row.allocated_amount) for row in self.allocations)
            if total_allocated > flt(self.paid_amount):
                frappe.throw(
                    _("Total allocated amount ({0}) exceeds the transaction amount ({1}).").format(
                        frappe.format_value(total_allocated, {"fieldtype": "Currency"}),
                        frappe.format_value(flt(self.paid_amount), {"fieldtype": "Currency"}),
                    )
                )

    # -----------------------------------------------------------------------
    # Submit
    # -----------------------------------------------------------------------
    def on_submit(self):
        if self.has_party:
            self.create_payment_entry()
        else:
            self.create_journal_entry()

    # -----------------------------------------------------------------------
    # Cancel
    # -----------------------------------------------------------------------
    def on_cancel(self):
        if self.linked_doc:
            linked_doctype = "Payment Entry" if self.has_party else "Journal Entry"
            try:
                doc_to_cancel = frappe.get_doc(linked_doctype, self.linked_doc)
                if doc_to_cancel.docstatus == 1:
                    doc_to_cancel.cancel()
                    frappe.msgprint(
                        _("Linked accounting document ({0}) has been cancelled.").format(self.linked_doc)
                    )
                else:
                    frappe.msgprint(
                        _("Linked document ({0}) was already in Draft or Cancelled state.").format(self.linked_doc)
                    )
            except frappe.DoesNotExistError:
                frappe.msgprint(
                    _("Warning: Linked document ({0}) was not found in the system.").format(self.linked_doc),
                    indicator="orange",
                )

    # -----------------------------------------------------------------------
    # Create Payment Entry
    # -----------------------------------------------------------------------
    def create_payment_entry(self):
        """Create a Payment Entry with invoice allocations."""
        # Receipt → Receive, Payment → Pay
        payment_type = "Receive" if self.transaction_type == "Receipt" else "Pay"
        company = self.company

        pe = frappe.new_doc("Payment Entry")
        pe.payment_type = payment_type
        pe.posting_date = self.posting_date
        pe.mode_of_payment = self.mode_of_payment
        pe.party_type = self.party_type
        pe.party = self.party
        pe.company = company
        pe.paid_amount = flt(self.paid_amount)
        pe.received_amount = flt(self.paid_amount)
        pe.remarks = self.remarks or _("Auto-generated from Lite Transaction: {0}").format(self.name)
        pe.reference_no = self.name
        pe.reference_date = self.posting_date

        # Add invoice references
        for ref in self.allocations:
            if flt(ref.allocated_amount) > 0:
                pe.append(
                    "references",
                    {
                        "reference_doctype": ref.reference_doctype,
                        "reference_name": ref.reference_name,
                        "total_amount": flt(ref.total_amount),
                        "outstanding_amount": flt(ref.outstanding_amount),
                        "allocated_amount": flt(ref.allocated_amount),
                    },
                )

        try:
            pe.setup_party_account_field()
            pe.set_missing_values()
            pe.set_exchange_rate()
        except Exception:
            pass

        pe.insert(ignore_permissions=True)
        pe.submit()

        frappe.db.set_value(self.doctype, self.name, "linked_doc", pe.name)
        frappe.msgprint(
            _("Payment Entry created: {0}").format(
                frappe.bold(frappe.utils.get_link_to_form("Payment Entry", pe.name))
            ),
            indicator="green",
        )

    # -----------------------------------------------------------------------
    # Create Journal Entry
    # -----------------------------------------------------------------------
    def create_journal_entry(self):
        """Create a double-entry Journal Entry for direct account transactions."""
        company = self.company

        # Get the default account for the chosen Mode of Payment
        mop_account = frappe.db.get_value(
            "Mode of Payment Account",
            {"parent": self.mode_of_payment, "company": company},
            "default_account",
        )

        if not mop_account:
            frappe.throw(
                _("Mode of Payment '{0}' has no default account for company '{1}'. Please configure it in Mode of Payment settings.").format(
                    self.mode_of_payment, company
                )
            )

        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.posting_date = self.posting_date
        je.company = company
        je.user_remark = self.remarks or _("Auto-generated from Lite Transaction: {0}").format(self.name)
        je.cheque_no = self.name
        je.cheque_date = self.posting_date

        # Receipt → Cash/Bank Dr, Income Cr
        # Payment → Expense Dr, Cash/Bank Cr
        if self.transaction_type == "Receipt":
            debit_acc = mop_account
            credit_acc = self.account
        else:
            debit_acc = self.account
            credit_acc = mop_account

        amount = flt(self.paid_amount)

        je.append(
            "accounts",
            {
                "account": debit_acc,
                "debit_in_account_currency": amount,
                "credit_in_account_currency": 0,
                "user_remark": self.remarks,
            },
        )
        je.append(
            "accounts",
            {
                "account": credit_acc,
                "debit_in_account_currency": 0,
                "credit_in_account_currency": amount,
                "user_remark": self.remarks,
            },
        )

        je.insert(ignore_permissions=True)
        je.submit()

        frappe.db.set_value(self.doctype, self.name, "linked_doc", je.name)
        frappe.msgprint(
            _("Journal Entry created: {0}").format(
                frappe.bold(frappe.utils.get_link_to_form("Journal Entry", je.name))
            ),
            indicator="green",
        )


# -----------------------------------------------------------------------
# Whitelisted API — جلب الفواتير غير المسددة
# -----------------------------------------------------------------------
@frappe.whitelist()
def get_outstanding_invoices(party_type, party, transaction_type, company=None):
    """
    Fetch outstanding documents for a given party by querying GL Entry directly.
    This captures ALL voucher types: Sales Invoice, Journal Entry, Purchase Invoice, etc.
    Called from the Client Script via frappe.call.
    """
    if not party_type or not party:
        frappe.throw(_("Please specify Party Type and Party."))

    if not company:
        company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
            "Global Defaults", "default_company"
        )

    # First try ERPNext's built-in function
    try:
        from erpnext.accounts.party import get_party_account

        party_account = get_party_account(party_type, party, company)

        args = frappe._dict(
            {
                "party_type": party_type,
                "party": party,
                "company": company,
                "party_account": party_account,
                "account": party_account,
                "voucher_type": "",
                "voucher_no": "",
                "cost_center": "",
                "against_all_invoices": True,
                "posting_date": frappe.utils.today(),
            }
        )

        from erpnext.accounts.doctype.payment_entry.payment_entry import (
            get_outstanding_reference_documents,
        )

        references = get_outstanding_reference_documents(args)
        if references:
            return references

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Finance Lite: get_outstanding_reference_documents failed — using GL Entry fallback",
        )

    # Fallback: query GL Entry directly — captures Sales Invoices, Journal Entries, and everything else
    return _get_outstanding_via_gl_entry(party_type, party, company)


def _get_outstanding_via_gl_entry(party_type, party, company):
    """
    Direct GL Entry query to find all outstanding amounts for a party,
    regardless of voucher type (Sales Invoice, Journal Entry, etc.).

    Logic:
    - Customer → outstanding = SUM(debit - credit) > 0  (money owed TO us)
    - Supplier/Employee → outstanding = SUM(credit - debit) > 0  (money we OWE)
    """
    if party_type == "Customer":
        # For customers: debit > credit means they still owe us money
        outstanding_expr = "SUM(gle.debit - gle.credit)"
    else:
        # For suppliers/employees: credit > debit means we owe them money
        outstanding_expr = "SUM(gle.credit - gle.debit)"

    results = frappe.db.sql(
        f"""
        SELECT
            gle.voucher_type,
            gle.voucher_no,
            {outstanding_expr} AS outstanding_amount,
            {outstanding_expr} AS invoice_amount
        FROM `tabGL Entry` gle
        WHERE
            gle.party_type = %(party_type)s
            AND gle.party = %(party)s
            AND gle.company = %(company)s
            AND gle.is_cancelled = 0
        GROUP BY
            gle.voucher_type,
            gle.voucher_no
        HAVING
            outstanding_amount > 0.005
        ORDER BY
            MIN(gle.posting_date) ASC
        """,
        {"party_type": party_type, "party": party, "company": company},
        as_dict=True,
    )

    # Enrich with total_amount from the source document where possible
    for row in results:
        row["total_amount"] = _get_voucher_total(row["voucher_type"], row["voucher_no"])
        if not row["total_amount"]:
            row["total_amount"] = row["outstanding_amount"]

    return results


def _get_voucher_total(voucher_type, voucher_no):
    """Fetch the original total amount from the source voucher document."""
    try:
        field_map = {
            "Sales Invoice": ("tabSales Invoice", "grand_total"),
            "Purchase Invoice": ("tabPurchase Invoice", "grand_total"),
            "Journal Entry": ("tabJournal Entry", "total_debit"),
            "Payment Entry": ("tabPayment Entry", "paid_amount"),
        }
        if voucher_type in field_map:
            table, field = field_map[voucher_type]
            return flt(frappe.db.get_value(table, voucher_no, field))
    except Exception:
        pass
    return 0
