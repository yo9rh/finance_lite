import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = []

    company = filters.get("company")
    cashier = filters.get("cashier")
    date = filters.get("date")

    if not company or not cashier or not date:
        return columns, data

    # Fetch Transactions created/owned by the selected cashier on the selected date
    transactions = frappe.get_all(
        "Lite Transaction",
        filters={
            "company": company,
            "owner": cashier,
            "posting_date": date,
            "docstatus": 1
        },
        fields=[
            "name",
            "posting_date",
            "transaction_type",
            "party_type",
            "party",
            "mode_of_payment",
            "currency",
            "exchange_rate",
            "paid_amount",
            "enable_discount",
            "discount_amount",
            "remarks"
        ],
        order_by="creation asc"
    )

    company_currency = frappe.get_cached_value("Company", company, "default_currency") or "IQD"

    # Currency summary dict
    summary_data = {}

    for tx in transactions:
        tx_currency = tx.currency or company_currency
        rate = flt(tx.exchange_rate) or 1.0
        
        paid_amt = flt(tx.paid_amount)
        base_paid_amt = paid_amt * rate
        discount_amt = flt(tx.discount_amount) if tx.enable_discount else 0.0

        receipt_amt = paid_amt if tx.transaction_type == "Receipt" else 0.0
        payment_amt = paid_amt if tx.transaction_type == "Payment" else 0.0

        # Update currency summary
        if tx_currency not in summary_data:
            summary_data[tx_currency] = {
                "receipts": 0.0,
                "payments": 0.0,
                "discounts": 0.0
            }
        summary_data[tx_currency]["receipts"] += receipt_amt
        summary_data[tx_currency]["payments"] += payment_amt
        summary_data[tx_currency]["discounts"] += discount_amt

        data.append({
            "name": tx.name,
            "posting_date": tx.posting_date,
            "transaction_type": _(tx.transaction_type),
            "party": f"{_(tx.party_type or '')}: {tx.party or ''}" if tx.party else "",
            "mode_of_payment": tx.mode_of_payment,
            "currency": tx_currency,
            "exchange_rate": rate,
            "paid_amount": paid_amt,
            "base_paid_amount": base_paid_amt,
            "discount_amount": discount_amt,
            "remarks": tx.remarks
        })

    # Prepare report summary cards
    report_summary = []
    for cur, val in summary_data.items():
        net_cash = val["receipts"] - val["payments"]
        report_summary.extend([
            {
                "value": val["receipts"],
                "indicator": "Green",
                "label": f"{_('Total Receipts')} ({cur})",
                "datatype": "Currency",
                "currency": cur
            },
            {
                "value": val["payments"],
                "indicator": "Red",
                "label": f"{_('Total Payments')} ({cur})",
                "datatype": "Currency",
                "currency": cur
            },
            {
                "value": net_cash,
                "indicator": "Blue" if net_cash >= 0 else "Orange",
                "label": f"{_('Net Cash Collected')} ({cur})",
                "datatype": "Currency",
                "currency": cur
            }
        ])

    return columns, data, None, None, report_summary

def get_columns():
    return [
        {
            "fieldname": "name",
            "label": _("Transaction ID / رقم السند"),
            "fieldtype": "Link",
            "options": "Lite Transaction",
            "width": 160
        },
        {
            "fieldname": "posting_date",
            "label": _("Date / التاريخ"),
            "fieldtype": "Date",
            "width": 110
        },
        {
            "fieldname": "transaction_type",
            "label": _("Type / النوع"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "party",
            "label": _("Party / الطرف"),
            "fieldtype": "Data",
            "width": 180
        },
        {
            "fieldname": "mode_of_payment",
            "label": _("Mode of Payment / طريقة الدفع"),
            "fieldtype": "Link",
            "options": "Mode of Payment",
            "width": 140
        },
        {
            "fieldname": "currency",
            "label": _("Currency / العملة"),
            "fieldtype": "Link",
            "options": "Currency",
            "width": 90
        },
        {
            "fieldname": "exchange_rate",
            "label": _("Exchange Rate / سعر الصرف"),
            "fieldtype": "Float",
            "width": 110
        },
        {
            "fieldname": "paid_amount",
            "label": _("Amount / المبلغ"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120
        },
        {
            "fieldname": "base_paid_amount",
            "label": _("Base Amount / المعادل بالعملة المحلية"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "discount_amount",
            "label": _("Discount / الخصم"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 100
        },
        {
            "fieldname": "remarks",
            "label": _("Remarks / ملاحظات"),
            "fieldtype": "Data",
            "width": 200
        }
    ]
