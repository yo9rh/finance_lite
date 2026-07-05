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

        // Filter for split accounts table
        frm.set_query('account', 'accounts', function() {
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
        frm.toggle_display(['sec_account', 'split_entries'], !is_party);

        frm.toggle_reqd(['party_type', 'party'], is_party);

        if (!is_party) {
            frm.set_value('party_type', '');
            frm.set_value('party', '');
            frm.clear_table('allocations');
            frm.refresh_field('allocations');
            frm.trigger('split_entries');
        } else {
            frm.set_value('account', '');
            frm.set_value('split_entries', 0);
            frm.clear_table('accounts');
            frm.refresh_field('accounts');
            frm.toggle_display(['account', 'accounts'], false);
            frm.toggle_reqd(['account'], false);
            frm.set_df_property('paid_amount', 'read_only', 0);
        }
    },

    split_entries: function(frm) {
        let split = frm.doc.split_entries && !frm.doc.has_party;
        frm.toggle_display(['account'], !frm.doc.has_party && !split);
        frm.toggle_reqd(['account'], !frm.doc.has_party && !split);
        frm.toggle_display(['accounts'], !frm.doc.has_party && split);
        frm.set_df_property('paid_amount', 'read_only', split ? 1 : 0);

        if (!split) {
            frm.clear_table('accounts');
            frm.refresh_field('accounts');
        } else {
            frm.set_value('account', '');
            frm.trigger('calculate_paid_amount_from_split');
        }
    },

    calculate_paid_amount_from_split: function(frm) {
        if (frm.doc.split_entries && !frm.doc.has_party) {
            let total = 0;
            (frm.doc.accounts || []).forEach(row => {
                total += flt(row.amount);
            });
            frm.set_value('paid_amount', total);
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

    enable_discount: function(frm) {
        if (!frm.doc.enable_discount) {
            frm.set_value('amount_before_discount', 0);
            frm.set_value('discount_percentage', 0);
            frm.set_value('discount_amount', 0);
        } else {
            if (!frm.doc.amount_before_discount) {
                frm.set_value('amount_before_discount', frm.doc.paid_amount);
            }
        }
    },

    amount_before_discount: function(frm) {
        if (frm.doc.enable_discount) {
            let discount_amt = (frm.doc.amount_before_discount || 0) * (frm.doc.discount_percentage || 0) / 100;
            frappe.model.set_value(frm.doctype, frm.docname, 'discount_amount', discount_amt);
            frappe.model.set_value(frm.doctype, frm.docname, 'paid_amount', (frm.doc.amount_before_discount || 0) - discount_amt);
        }
    },

    discount_percentage: function(frm) {
        if (frm.doc.enable_discount) {
            let discount_amt = (frm.doc.amount_before_discount || 0) * (frm.doc.discount_percentage || 0) / 100;
            frappe.model.set_value(frm.doctype, frm.docname, 'discount_amount', discount_amt);
            frappe.model.set_value(frm.doctype, frm.docname, 'paid_amount', (frm.doc.amount_before_discount || 0) - discount_amt);
        }
    },

    discount_amount: function(frm) {
        if (frm.doc.enable_discount && frm.doc.amount_before_discount) {
            let pct = ((frm.doc.discount_amount || 0) / frm.doc.amount_before_discount) * 100;
            frappe.model.set_value(frm.doctype, frm.docname, 'discount_percentage', pct);
            frappe.model.set_value(frm.doctype, frm.docname, 'paid_amount', frm.doc.amount_before_discount - (frm.doc.discount_amount || 0));
        }
    },

    get_invoices: function(frm) {
        if (!frm.doc.party_type || !frm.doc.party) {
            frappe.msgprint(__('Please select Party Type and Party first.'));
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
                    
                    // Base the unallocated amount on the amount before discount if discount is enabled
                    let unallocated_amount = frm.doc.enable_discount ? flt(frm.doc.amount_before_discount) : flt(frm.doc.paid_amount);
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
                        child.account = row.account;  // Important for precise reconciliation
                        child.total_amount = row.total_amount || row.invoice_amount;
                        child.outstanding_amount = row.outstanding_amount;
                        child.allocated_amount = allocate_now;
                    });
                    frm.refresh_field('allocations');

                    let msg = __('Successfully fetched {0} outstanding invoice(s).', [r.message.length]);
                    if (has_allocated) {
                        msg += '<br>' + __('The amount has been automatically allocated based on the total amount.');
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

frappe.ui.form.on('Lite Transaction Account', {
    amount: function(frm, cdt, cdn) {
        frm.trigger('calculate_paid_amount_from_split');
    },
    accounts_remove: function(frm) {
        frm.trigger('calculate_paid_amount_from_split');
    }
});
