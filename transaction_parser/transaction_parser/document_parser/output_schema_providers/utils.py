import frappe
from frappe import _

from transaction_parser.transaction_parser.document_parser.output_schema_providers import (
    OUTPUT_SCHEMA_PROVIDERS,
)


def get_output_schema_provider(country, doctype):
    schema_provider = OUTPUT_SCHEMA_PROVIDERS.get(country, {}).get(doctype)

    if not schema_provider:
        schema_provider = OUTPUT_SCHEMA_PROVIDERS.get("DEFAULT", {}).get(doctype)

    if not schema_provider:
        frappe.throw(_(f"No output schema provider found for {doctype}"))

    return schema_provider
