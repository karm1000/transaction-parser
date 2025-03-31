import frappe
from frappe import _
from frappe.utils import cint, cstr

from transaction_parser.transaction_parser.controllers import get_controller
from transaction_parser.transaction_parser.utils import is_enabled
from transaction_parser.transaction_parser.utils.notification import (
    enqueue_notification,
)


@frappe.whitelist()
def parse(doctype, country, file_url, page_limit=None):
    is_enabled()

    frappe.has_permission(doctype, "write", throw=True)

    frappe.enqueue(
        _parse,
        country=cstr(country),
        doctype=cstr(doctype),
        file_url=cstr(file_url),
        page_limit=cint(page_limit),
    )


def _parse(country, doctype, file_url, page_limit=None):
    try:
        file = None
        filename = file_url.split("/")[-1]

        file = frappe.get_last_doc("File", filters={"file_url": file_url})
        filename = file.file_name

        controller = get_controller(country, doctype)()
        doc = controller.generate(file, page_limit)

        notification = {
            "document_type": doctype,
            "document_name": doc.name,
            "subject": _(f"{doctype} {doc.name} generated from {filename}"),
        }

    except Exception:
        error_log = frappe.log_error(
            "Transaction Parser API Error",
            reference_doctype="File",
            reference_name=file.name if file else filename,
        )

        notification = {
            "document_type": error_log.doctype,
            "document_name": error_log.name,
            "subject": _(f"Failed to generate {doctype} from {filename}"),
        }

    finally:
        enqueue_notification(**notification)
