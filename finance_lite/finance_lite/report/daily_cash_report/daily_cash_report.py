import frappe
from frappe import _
from frappe.utils import flt, getdate

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    company = filters.get("company")
    date = filters.get("date")

    if not company or not date:
        return columns, data

    # 1. Fetch Mode of Payment accounts
    mop_accounts = frappe.get_all(
        "Mode of Payment Account",
        filters={"company": company},
        pluck="default_account"
    )
    mop_accounts = list(set([acc for acc in mop_accounts if acc]))

    if not mop_accounts:
        return columns, data

    # 2. Calculate Opening Balance of Cash/Bank
    opening_bal = 0.0
    for acc in mop_accounts:
        from erpnext.accounts.utils import get_balance_on
        from datetime import timedelta
        # Balance before the date (date - 1 day)
        prev_date = getdate(date) - timedelta(days=1)
        bal = flt(get_balance_on(account=acc, date=prev_date, company=company))
        opening_bal += bal

    # Add Opening Balance Row
    data.append({
        "voucher_no": _("Opening Balance / الرصيد الافتتاحي"),
        "receipt_amount": opening_bal if opening_bal >= 0 else 0,
        "payment_amount": abs(opening_bal) if opening_bal < 0 else 0,
        "remarks": _("Beginning Cash Balance")
    })

    # 3. Fetch Transactions for the day
    transactions = frappe.get_all(
        "Lite Transaction",
        filters={
            "company": company,
            "posting_date": date,
            "docstatus": 1
        },
        fields=[
            "name",
            "posting_date",
            "transaction_type",
            "party",
            "mode_of_payment",
            "paid_amount",
            "remarks"
        ],
        order_by="creation asc"
    )

    total_receipts = 0.0
    total_payments = 0.0

    for tx in transactions:
        receipt = flt(tx.paid_amount) if tx.transaction_type == "Receipt" else 0.0
        payment = flt(tx.paid_amount) if tx.transaction_type == "Payment" else 0.0
        
        total_receipts += receipt
        total_payments += payment

        data.append({
            "voucher_no": tx.name,
            "posting_date": tx.posting_date,
            "party": tx.party or tx.mode_of_payment,
            "mode_of_payment": tx.mode_of_payment,
            "receipt_amount": receipt,
            "payment_amount": payment,
            "remarks": tx.remarks
        })

    # 4. Closing Balance Row
    closing_bal = opening_bal + total_receipts - total_payments
    data.append({
        "voucher_no": _("Closing Balance / الرصيد الختامي"),
        "receipt_amount": closing_bal if closing_bal >= 0 else 0,
        "payment_amount": abs(closing_bal) if closing_bal < 0 else 0,
        "remarks": _("Ending Cash Balance")
    })

    return columns, data

def get_columns():
    return [
        {
            "fieldname": "voucher_no",
            "label": _("رقم السند (Voucher No)"),
            "fieldtype": "Data",
            "width": 180
        },
        {
            "fieldname": "posting_date",
            "label": _("التاريخ (Posting Date)"),
            "fieldtype": "Date",
            "width": 110
        },
        {
            "fieldname": "party",
            "label": _("الطرف / الحساب (Party / Account)"),
            "fieldtype": "Data",
            "width": 180
        },
        {
            "fieldname": "mode_of_payment",
            "label": _("طريقة الدفع (MOP)"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "receipt_amount",
            "label": _("المقبوضات (Receipt Amount)"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "payment_amount",
            "label": _("المدفوعات (Payment Amount)"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "remarks",
            "label": _("البيان (Remarks)"),
            "fieldtype": "Data",
            "width": 200
        }
    ]
