# Copyright (c) 2025, Resilient Tech and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document

from transaction_parser.transaction_parser.utils import to_dict

DOCTYPE = "Transaction Parser Settings"


class TransactionParserSettings(Document):
    # TODO: can we check API creds?
    def validate(self):
        self._validate_json_fields()

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
    frappe.has_permission(DOCTYPE)

    default_model = frappe.get_cached_value(DOCTYPE, None, "default_ai_model")
    supported_models = frappe.get_meta(DOCTYPE).get_field("default_ai_model").options

    return {
        "default_model": default_model,
        "supported_models": supported_models,
    }
