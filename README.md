# Finance Lite

Finance Lite is a simplified receipts and payments interface for ERPNext.
It hides accounting complexity from end users while maintaining full
double-entry bookkeeping integrity in the background.

## Features
- Simplified receipts (قبض) and payments (صرف) entry
- Automatic Payment Entry generation when a party (Customer/Supplier/Employee) is involved
- Automatic Journal Entry generation for direct account transactions
- Invoice allocation for outstanding invoices
- Professional Arabic print format (receipt/voucher)

## Installation

```bash
bench get-app finance_lite
bench --site [your-site-name] install-app finance_lite
```

## License
MIT
