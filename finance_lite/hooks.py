app_name = "finance_lite"
app_title = "Finance Lite"
app_publisher = "Administrator"
app_description = "Finance Lite - Simplified Receipts and Payments for ERPNext"
app_email = "admin@example.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "finance_lite",
# 		"logo": "/assets/finance_lite/logo.png",
# 		"title": "Finance Lite",
# 		"route": "/finance_lite",
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/finance_lite/css/finance_lite.css"
# app_include_js = "/assets/finance_lite/js/finance_lite.js"

# include js, css files in header of web template
# web_include_css = "/assets/finance_lite/css/finance_lite.css"
# web_include_js = "/assets/finance_lite/js/finance_lite.js"

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "finance_lite/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "finance_lite.utils.jinja_methods",
# 	"filters": "finance_lite.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "finance_lite.install.before_install"
# after_install = "finance_lite.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "finance_lite.uninstall.before_uninstall"
# after_uninstall = "finance_lite.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "finance_lite.notifications.get_notification_config"

# Permissions
# -----------

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"finance_lite.tasks.all"
# 	],
# 	"daily": [
# 		"finance_lite.tasks.daily"
# 	],
# 	"hourly": [
# 		"finance_lite.tasks.hourly"
# 	],
# 	"weekly": [
# 		"finance_lite.tasks.weekly"
# 	],
# 	"monthly": [
# 		"finance_lite.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "finance_lite.install.before_tests"

# Overriding Methods
# ------------------------------

# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "finance_lite.event.get_events"
# }

# Request Events
# ----------------
# before_request = ["finance_lite.utils.before_request"]
# after_request = ["finance_lite.utils.after_request"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"finance_lite.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
    {
        "dt": "Print Format",
        "filters": [
            ["module", "=", "Finance Lite"]
        ]
    }
]
