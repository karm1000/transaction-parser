import frappe
from frappe import _
from frappe.utils import cint, cstr

from transaction_parser.transaction_parser.controllers import get_controller
from transaction_parser.transaction_parser.utils import is_enabled
from transaction_parser.transaction_parser.utils.notification import (
    enqueue_notification,
)


@frappe.whitelist()
def parse(doctype, country, file_url, ai_model=None, page_limit=None):
    is_enabled()

    frappe.has_permission(doctype, "create", throw=True)

    frappe.enqueue(
        _parse,
        country=cstr(country),
        doctype=cstr(doctype),
        file_url=cstr(file_url),
        ai_model=cstr(ai_model),
        page_limit=cint(page_limit),
        queue="long",
    )


def _parse(
    country,
    doctype,
    file_url,
    ai_model=None,
    page_limit=None,
    user=None,
    party=None,
    default_company=None,
):
    try:
        file = None
        filename = file_url.split("/")[-1]

        file = frappe.get_last_doc("File", filters={"file_url": file_url})
        filename = file.file_name

        controller = get_controller(country, doctype)(user, party, default_company)
        doc = controller.generate(file, ai_model, page_limit)

        notification = {
            "document_type": doctype,
            "document_name": doc.name,
            "subject": _("{0} {1} generated from {2}").format(
                _(doctype),
                doc.name,
                filename,
            ),
        }

    except Exception:
        error_log = frappe.log_error(
            "Transaction Parser API Error",
            reference_doctype="File",
            reference_name=file.name if file else filename,
        )
        message = _("Failed to generate {0} from {1}").format(_(doctype), filename)

        notification = {
            "document_type": error_log.doctype,
            "document_name": error_log.name,
            "subject": message,
        }

        email_failure(user, message)

    finally:
        enqueue_notification(**notification)


def email_failure(user, message):
    if not user:
        return

    recipient = frappe.db.get_value("User", user, "email")

    # TODO: better msg and subject
    frappe.sendmail(
        recipients=recipient,
        subject=_("Transaction Parser Error"),
        message=message,
    )
