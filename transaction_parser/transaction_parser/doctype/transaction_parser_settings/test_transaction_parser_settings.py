"""Tests for Transaction Parser Settings validations and helpers."""

import re

import frappe
from frappe.tests.utils import FrappeTestCase

from transaction_parser.tests.utils import change_settings

DOCTYPE = "Transaction Parser Settings"


class TestTransactionParserSettings(FrappeTestCase):
    def setUp(self):
        self.settings = frappe.get_cached_doc(DOCTYPE)

    def tearDown(self):
        frappe.db.rollback()

    def test_validate_lookback_count_must_be_positive(self):
        self.settings.reload()
        self.settings.flags.ignore_permissions = True
        self.settings.invoice_lookback_count = -5
        self.assertRaisesRegex(
            frappe.ValidationError,
            re.compile(r"(.*must be greater than 0.*)"),
            self.settings.save,
        )

    # ----------------------
    # Email configurations
    # ----------------------
    @change_settings({"parse_incoming_emails": 1, "incoming_email_accounts": []})
    def test_duplicate_incoming_email_accounts_throws_when_enabled(self):
        self.settings.reload()
        self.settings.append(
            "incoming_email_accounts",
            {
                "transaction": "Sales Order",
                "to_email": "inbox@example.com",
                "user": frappe.session.user,
                "company": "_Test Company",
            },
        )
        self.settings.append(
            "incoming_email_accounts",
            {
                "transaction": "Expense",
                "to_email": "inbox@example.com",  # duplicate to_email
                "user": frappe.session.user,
                "company": "_Test Company",
            },
        )

        self.assertRaisesRegex(
            frappe.ValidationError,
            re.compile(r"Duplicate email account .* in incoming email accounts."),
            self.settings.save,
        )

    @change_settings({"parse_incoming_emails": 1, "party_emails": []})
    def test_duplicate_party_emails_throws_when_enabled(self):
        self.settings.reload()
        customer = "_Test TP Customer"
        self.settings.append(
            "party_emails",
            {
                "party_type": "Customer",
                "party": customer,
                "party_email": "notify@cust.com",
            },
        )
        self.settings.append(
            "party_emails",
            {
                "party_type": "Customer",
                "party": customer,
                "party_email": "notify@cust.com",  # duplicate for same type
            },
        )

        self.assertRaisesRegex(
            frappe.ValidationError,
            re.compile(r"Duplicate email .* for party type .*"),
            self.settings.save,
        )

    # ----------------------
    # JSON field validations
    # ----------------------
    def test_invalid_json_fields(self):
        for field in [
            "base_schema",
            "tax_schema",
            "address_schema",
            "party_schema",
            "item_schema",
        ]:
            self.settings.reload()
            self.settings.set(field, "{invalid json}")
            self.assertRaisesRegex(
                frappe.ValidationError,
                re.compile(r"Please provide a valid JSON value for .*"),
                self.settings.save,
            )
