// Copyright (c) 2026, Administrator and contributors
// For license information, please see license.txt

frappe.ui.form.on('Lite Transaction', {
    setup: function(frm) {
        // Filter allowed party types
        frm.set_query('party_type', function() {
            return {
                filters: {
                    name: ['in', ['Customer', 'Supplier', 'Employee']]
                }
            };
        });

        // Filter to leaf-level expense/income accounts only
        frm.set_query('account', function() {
            return {
                filters: {
                    company: frm.doc.company,
                    account_type: ['in', [
                        'Income Account', 'Expense Account',
                        'Direct Income', 'Direct Expense',
                        'Indirect Income', 'Indirect Expense'
                    ]],
                    is_group: 0
                }
            };
        });
    },

    refresh: function(frm) {
        frm.trigger('has_party');
        frm.trigger('_add_custom_buttons');
    },

    _add_custom_buttons: function(frm) {
        frm.clear_custom_buttons();

        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('General Ledger'), function() {
                frappe.route_options = {
                    voucher_no: frm.doc.name,
                    from_date: frm.doc.posting_date,
                    to_date: frm.doc.posting_date,
                    company: frm.doc.company
                };
                frappe.set_route("query-report", "General Ledger");
            }, __('Accounting'));

            frm.add_custom_button(__('Print Receipt'), function() {
                frappe.utils.print(frm.doctype, frm.docname, 'إيصال مالي');
            });
        }
    },

    company: function(frm) {
        // Clear party and account when company changes
        frm.set_value('party', '');
        frm.set_value('account', '');
        frm.clear_table('allocations');
        frm.refresh_field('allocations');
    },

    has_party: function(frm) {
        let is_party = frm.doc.has_party;

        frm.toggle_display(['party_type', 'party', 'col_break_party',
            'sec_alloc', 'get_invoices', 'allocations'], is_party);
        frm.toggle_display(['sec_account', 'account'], !is_party);

        frm.toggle_reqd(['party_type', 'party'], is_party);
        frm.toggle_reqd(['account'], !is_party);

        if (!is_party) {
            frm.set_value('party_type', '');
            frm.set_value('party', '');
            frm.clear_table('allocations');
            frm.refresh_field('allocations');
        } else {
            frm.set_value('account', '');
        }
    },

    transaction_type: function(frm) {
        frm.set_value('party', '');
        frm.clear_table('allocations');
        frm.refresh_field('allocations');
    },

    party_type: function(frm) {
        frm.set_value('party', '');
        frm.clear_table('allocations');
        frm.refresh_field('allocations');
    },

    party: function(frm) {
        frm.clear_table('allocations');
        frm.refresh_field('allocations');
    },

    get_invoices: function(frm) {
        if (!frm.doc.party_type) {
            frappe.msgprint(__('Please select Party Type first'));
            return;
        }
        if (!frm.doc.party) {
            frappe.msgprint(__('Please select Party first'));
            return;
        }

        frappe.call({
            method: 'finance_lite.finance_lite.doctype.lite_transaction.lite_transaction.get_outstanding_invoices',
            args: {
                party_type: frm.doc.party_type,
                party: frm.doc.party,
                transaction_type: frm.doc.transaction_type,
                company: frm.doc.company
            },
            freeze: true,
            freeze_message: __('Fetching invoices...'),
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    frm.clear_table('allocations');
                    let unallocated_amount = flt(frm.doc.paid_amount);
                    let has_allocated = false;

                    r.message.forEach(function(row) {
                        let allocate_now = 0;
                        if (unallocated_amount > 0) {
                            if (unallocated_amount >= row.outstanding_amount) {
                                allocate_now = row.outstanding_amount;
                            } else {
                                allocate_now = unallocated_amount;
                            }
                            unallocated_amount -= allocate_now;
                            has_allocated = true;
                        }

                        let child = frm.add_child('allocations');
                        child.reference_doctype = row.voucher_type;
                        child.reference_name = row.voucher_no;
                        child.total_amount = row.total_amount || row.invoice_amount;
                        child.outstanding_amount = row.outstanding_amount;
                        child.allocated_amount = allocate_now;
                    });
                    frm.refresh_field('allocations');

                    let msg = __('Successfully fetched {0} outstanding invoice(s).', [r.message.length]);
                    if (has_allocated) {
                        msg += '<br>' + __('The amount has been automatically allocated based on the paid amount.');
                    }

                    frappe.msgprint({
                        title: __('Done'),
                        indicator: 'green',
                        message: msg
                    });
                } else {
                    frappe.msgprint({
                        title: __('No Invoices'),
                        indicator: 'blue',
                        message: __('No outstanding invoices found for this party.')
                    });
                }
            }
        });
    },

    validate: function(frm) {
        if (frm.doc.has_party && frm.doc.allocations && frm.doc.allocations.length > 0) {
            let total_allocated = frm.doc.allocations.reduce(function(sum, row) {
                return sum + (row.allocated_amount || 0);
            }, 0);

            if (total_allocated > frm.doc.paid_amount) {
                frappe.msgprint({
                    title: __('Allocation Error'),
                    indicator: 'red',
                    message: __('Total allocated amount ({0}) exceeds the transaction amount ({1}).', [
                        format_currency(total_allocated),
                        format_currency(frm.doc.paid_amount)
                    ])
                });
                frappe.validated = false;
            }
        }
    }
});

// Child table row validation
frappe.ui.form.on('Lite Transaction Reference', {
    allocated_amount: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (flt(row.allocated_amount) > flt(row.outstanding_amount)) {
            frappe.model.set_value(cdt, cdn, 'allocated_amount', row.outstanding_amount);
            frappe.msgprint({
                title: __('Allocation Error'),
                indicator: 'orange',
                message: __('Allocated amount cannot exceed the outstanding amount ({0}).', [
                    format_currency(row.outstanding_amount)
                ])
            });
        }
    }
});
