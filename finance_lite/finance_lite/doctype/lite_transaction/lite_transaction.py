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
        if self.has_party:
            if not self.party_type or not self.party:
                frappe.throw(_("Party Type and Party are mandatory when 'Has Party' is checked."))

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
    # Submit / Cancel
    # -----------------------------------------------------------------------
    def on_submit(self):
        self.make_gl_entries()

    def on_cancel(self):
        self.make_gl_entries(cancel=True)

    # -----------------------------------------------------------------------
    # General Ledger Entries
    # -----------------------------------------------------------------------
    def make_gl_entries(self, cancel=False):
        """Create GL Entries and Payment Ledger Entries for this transaction."""
        from erpnext.accounts.general_ledger import make_gl_entries

        gl_entries = []

        # 1. Get Mode of Payment Account
        mop_account = frappe.db.get_value(
            "Mode of Payment Account",
            {"parent": self.mode_of_payment, "company": self.company},
            "default_account",
        )
        if not mop_account:
            frappe.throw(
                _("Mode of Payment '{0}' has no default account for company '{1}'.").format(
                    self.mode_of_payment, self.company
                )
            )

        # 2. Determine Opposing Account
        if self.has_party:
            from erpnext.accounts.party import get_party_account
            opposing_account = get_party_account(self.party_type, self.party, self.company)
            if not opposing_account:
                frappe.throw(_("Please set a default account for {0} {1}").format(self.party_type, self.party))
        else:
            opposing_account = self.account
            if not opposing_account:
                frappe.throw(_("Expense / Income Account is mandatory when there is no party."))

        amount = flt(self.paid_amount)
        cost_center = frappe.get_cached_value("Company", self.company, "cost_center")

        def get_gl_dict(account, debit, credit, against_acc, against_v_type=None, against_v=None):
            return frappe._dict({
                "company": self.company,
                "posting_date": self.posting_date,
                "voucher_type": self.doctype,
                "voucher_no": self.name,
                "account": account,
                "against": against_acc,
                "debit": debit,
                "credit": credit,
                "debit_in_account_currency": debit,
                "credit_in_account_currency": credit,
                "against_voucher_type": against_v_type,
                "against_voucher": against_v,
                "party_type": self.party_type if account == opposing_account and self.has_party else None,
                "party": self.party if account == opposing_account and self.has_party else None,
                "remarks": self.remarks or _("Finance Lite Transaction"),
                "cost_center": cost_center
            })

        # 3. Add MOP Account Entry
        # MOP account is debited if Receipt, credited if Payment. The amount is paid_amount.
        if self.transaction_type == "Receipt":
            gl_entries.append(get_gl_dict(mop_account, amount, 0, opposing_account))
        else:
            gl_entries.append(get_gl_dict(mop_account, 0, amount, opposing_account))

        # 3.5 Handle Discount Entry
        if self.enable_discount and flt(self.discount_amount) > 0:
            if not self.discount_account:
                frappe.throw(_("Discount Account is mandatory when discount is enabled."))
            if self.transaction_type == "Receipt":
                # Discount Allowed is an expense (Debit)
                gl_entries.append(get_gl_dict(self.discount_account, flt(self.discount_amount), 0, opposing_account))
            else:
                # Discount Received is an income (Credit)
                gl_entries.append(get_gl_dict(self.discount_account, 0, flt(self.discount_amount), opposing_account))

        # 4. Add Opposing Account Entry (Split by allocations if necessary)
        # The opposing entry total must be amount_before_discount if discount is enabled, else paid_amount
        total_party_amount = flt(self.amount_before_discount) if self.enable_discount else amount

        if self.has_party and self.allocations:
            allocated_total = 0
            for ref in self.allocations:
                allocated_amt = flt(ref.allocated_amount)
                if allocated_amt > 0:
                    allocated_total += allocated_amt
                    # Use specific account from allocation if available, else fallback to default opposing
                    row_account = ref.account or opposing_account
                    
                    if self.transaction_type == "Receipt":
                        # Customer paying us -> credit customer
                        gl_entries.append(
                            get_gl_dict(row_account, 0, allocated_amt, mop_account, ref.reference_doctype, ref.reference_name)
                        )
                    else:
                        # We paying supplier -> debit supplier
                        gl_entries.append(
                            get_gl_dict(row_account, allocated_amt, 0, mop_account, ref.reference_doctype, ref.reference_name)
                        )

            # Unallocated remainder
            unallocated = total_party_amount - allocated_total
            if unallocated > 0:
                if self.transaction_type == "Receipt":
                    gl_entries.append(get_gl_dict(opposing_account, 0, unallocated, mop_account))
                else:
                    gl_entries.append(get_gl_dict(opposing_account, unallocated, 0, mop_account))
        else:
            # Full amount unallocated or no party
            if self.transaction_type == "Receipt":
                gl_entries.append(get_gl_dict(opposing_account, 0, total_party_amount, mop_account))
            else:
                gl_entries.append(get_gl_dict(opposing_account, total_party_amount, 0, mop_account))

        make_gl_entries(gl_entries, cancel=cancel, adv_adj=True, merge_entries=False)


# -----------------------------------------------------------------------
# Whitelisted API — جلب الفواتير غير المسددة
# -----------------------------------------------------------------------
@frappe.whitelist()
def get_outstanding_invoices(party_type, party, transaction_type, company=None):
    """
    Fetch outstanding documents for a given party by querying GL Entry directly.
    This captures ALL voucher types: Sales Invoice, Journal Entry, Purchase Invoice, etc.
    """
    if not party_type or not party:
        frappe.throw(_("Please specify Party Type and Party."))

    if not company:
        company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
            "Global Defaults", "default_company"
        )

    # We skip ERPNext's built-in get_outstanding_reference_documents because it 
    # doesn't reliably return the exact GL account for Journal Entries in all cases.
    return _get_outstanding_via_gl_entry(party_type, party, company)


def _get_outstanding_via_gl_entry(party_type, party, company):
    """
    Direct GL Entry query to find all outstanding amounts for a party.
    Also fetches the exact 'account' from the GL Entry so reconciliation works perfectly.
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
            gle.account,
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
            gle.voucher_no,
            gle.account
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
