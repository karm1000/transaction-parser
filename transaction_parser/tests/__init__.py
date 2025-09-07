from functools import partial

import frappe
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete
from frappe.test_runner import make_test_objects
from frappe.utils import getdate


def before_tests():
    frappe.clear_cache()

    if not frappe.db.a_row_exists("Company"):
        today = getdate()
        year = today.year if today.month > 3 else today.year - 1

        setup_complete(
            {
                "currency": "INR",
                "full_name": "Test User",
                "company_name": "Wind Power LLP",
                "timezone": "Asia/Kolkata",
                "company_abbr": "WP",
                "industry": "Manufacturing",
                "country": "India",
                "fy_start_date": f"{year}-04-01",
                "fy_end_date": f"{year + 1}-03-31",
                "language": "English",
                "company_tagline": "Testing",
                "email": "test@example.com",
                "password": "test",
                "chart_of_accounts": "Standard",
            }
        )

    create_test_records()
    frappe.db.commit()
    set_default_company_for_tests()
    setup_transaction_parser_settings()

    frappe.flags.country = "India"
    frappe.flags.skip_test_records = True
    frappe.enqueue = partial(frappe.enqueue, now=True)


def create_test_records():
    test_records = frappe.get_file_json(
        frappe.get_app_path("transaction_parser", "tests", "test_records.json")
    )
    for doctype, data in test_records.items():
        make_test_objects(doctype, data, commit=True)


def set_default_company_for_tests():
    frappe.db.set_value(
        "Company",
        "_Test Company",
        {
            "default_discount_account": "Discount Allowed - TC",
        },
    )

    # set default company
    global_defaults = frappe.get_single("Global Defaults")
    global_defaults.default_company = "_Test Company"
    global_defaults.save()


def setup_transaction_parser_settings():
    frappe.db.set_value(
        "Transaction Parser Settings", None, {"enabled": 1, "invoice_lookback_count": 5}
    )
