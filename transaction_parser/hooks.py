app_name = "transaction_parser"
app_title = "Transaction Parser"
app_publisher = "Resilient Tech"
app_description = "AI-powered add-on for ERPNext that extracts data from PDFs and creates draft records automatically."
app_email = "info@resilient.tech"
app_license = "GNU General Public License (v3)"
required_apps = ["frappe/erpnext"]

before_uninstall = "transaction_parser.uninstall.before_uninstall"
after_install = "transaction_parser.install.after_install"

app_include_js = "transaction_parser.bundle.js"

doctype_list_js = {
    "Sales Order": "transaction_parser/client_scripts/sales_order_list.js",
}

doc_events = {
    "Communication": {
        "on_update": "transaction_parser.transaction_parser.overrides.communication.on_update",
    }
}
