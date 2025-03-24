import frappe
from frappe import _
from frappe.utils import cint

from transaction_parser.transaction_parser.document_generators import (
    get_document_generator,
)
from transaction_parser.transaction_parser.document_parser.parser import DocumentParser
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
        country=country,
        doctype=doctype,
        file_url=file_url,
        page_limit=cint(page_limit),
    )


def _parse(country, doctype, file_url, page_limit=None):
    parser = DocumentParser()
    generator = get_document_generator(country, doctype)

    parsed_data = parser.parse(country, doctype, file_url, page_limit)
    doc = generator().generate(parsed_data)

    attach_file(doc, file_url)

    enqueue_notification(
        document_type=doctype,
        document_name=doc.name,
        subject=_(f"{doctype} {doc.name} has been created"),
    )


def attach_file(doc, file_url):
    file = frappe.get_last_doc("File", {"file_url": file_url})

    file.attached_to_doctype = doc.doctype
    file.attached_to_name = doc.name

    file.save()
