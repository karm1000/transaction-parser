app_name = "transaction_parser"
app_title = "Transaction Parser"
app_publisher = "Resilient Tech"
app_description = "AI-powered add-on for ERPNext that extracts data from PDFs and creates draft records automatically."
app_email = "info@resilient.tech"
app_license = "GNU General Public License (v3)"
required_apps = ["frappe/erpnext"]

after_install = "transaction_parser.install.after_install"

doctype_list_js = {
    "Sales Order": "transaction_parser/client_scripts/sales_order_list.js",
}
