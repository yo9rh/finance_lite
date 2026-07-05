frappe.query_reports["Daily Cash Report"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("الشركة (Company)"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname": "date",
			"label": __("التاريخ (Date)"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		}
	]
};
