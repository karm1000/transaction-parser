import json

import frappe
from frappe import _

from transaction_parser.transaction_parser.utils.__init__ import pretty_json

SERVICE_NAME = "Transaction Parser API"

PRETTY_JSON_FIELDS = [
    "request_headers",
    "data",
    "output",
    "error",
]


def enqueue_integration_request(**kwargs):
    frappe.enqueue(create_integration_request, **kwargs)


def create_integration_request(**kwargs):
    for field in PRETTY_JSON_FIELDS:
        if field in kwargs:
            kwargs[field] = pretty_json(kwargs[field])

    return frappe.get_doc(
        {
            "doctype": "Integration Request",
            "integration_request_service": SERVICE_NAME,
            "status": "Failed" if kwargs.get("error") else "Completed",
            **kwargs,
        }
    ).insert(ignore_permissions=True)
