# Copyright (c) 2025, Resilient Tech and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form

from transaction_parser.transaction_parser.utils import to_dict

DOCTYPE = "Transaction Parser Settings"


class TransactionParserSettings(Document):
    # TODO: can we check API creds?
    def validate(self):
        self._validate_incoming_email_accounts()
        self._validate_json_fields()

    def _validate_incoming_email_accounts(self):
        if len(self.incoming_email_accounts) != len(
            set(
                incoming_email_account.email_account
                for incoming_email_account in self.incoming_email_accounts
            )
        ):
            frappe.throw(
                _("Incoming Email Accounts must be unique."),
                title=_("Duplicate Incoming Email Accounts"),
            )

        for account in self.incoming_email_accounts:
            self._validate_incoming_email_account(account.email_account)

    def _validate_incoming_email_account(self, account_name: str):
        if not frappe.db.get_value("Email Account", account_name, "enable_incoming"):
            frappe.throw(
                _(
                    f"Email Account {get_link_to_form('Email Account', account_name)} must have incoming emails enabled."
                ),
                title=_("Invalid Incoming Email Account"),
            )

    def _validate_json_fields(self):
        for field in self.meta.fields:
            self._validate_json_field(field)

    def _validate_json_field(self, field):
        if field.fieldtype != "JSON":
            return

        value = self.get(field.fieldname)
        if not value:
            return

        try:
            to_dict(value)
        except Exception:
            frappe.throw(_(f"Please provide a valid JSON value for {field.label}"))


@frappe.whitelist()
def get_ai_models():
    default_model = frappe.get_cached_value(DOCTYPE, None, "default_ai_model")
    supported_models = frappe.get_meta(DOCTYPE).get_field("default_ai_model").options

    return {
        "default_model": default_model,
        "supported_models": supported_models,
    }
