import frappe
from frappe import _
from frappe.utils import cint, cstr

from transaction_parser.transaction_parser.controllers import get_controller
from transaction_parser.transaction_parser.utils import is_enabled
from transaction_parser.transaction_parser.utils.notification import (
    enqueue_notification,
)


@frappe.whitelist()
def parse(transaction, country, file_url, ai_model=None, page_limit=None):
    is_enabled()

    frappe.has_permission(transaction, "create", throw=True)

    frappe.enqueue(
        _parse,
        country=cstr(country),
        transaction=cstr(transaction),
        file_url=cstr(file_url),
        ai_model=cstr(ai_model),
        page_limit=cint(page_limit),
        queue="long",
    )


def _parse(
    country,
    transaction,
    file_url,
    ai_model=None,
    page_limit=None,
    user=None,
    party=None,
    company=None,
):
    try:
        file = None
        filename = file_url.split("/")[-1]

        file = frappe.get_last_doc("File", filters={"file_url": file_url})
        filename = file.file_name

        controller = get_controller(country, transaction)(party=party, company=company)
        doc = controller.generate(file, ai_model, page_limit)

        notification = {
            "document_type": transaction,
            "document_name": doc.name,
            "subject": _("{0} {1} generated from {2}").format(
                _(transaction),
                doc.name,
                filename,
            ),
        }

    except Exception as e:
        error_log = frappe.log_error(
            "Transaction Parser API Error",
            reference_doctype="File",
            reference_name=file.name if file else filename,
        )
        message = _("Failed to generate {0} from {1}").format(_(transaction), filename)

        notification = {
            "document_type": error_log.doctype,
            "document_name": error_log.name,
            "subject": message,
        }

        email_failure(user, message, str(e), file_url)

    finally:
        enqueue_notification(**notification)


def email_failure(user, subject, error_message, file_url):
    recipient = frappe.db.get_value("User", user, "email")

    frappe.sendmail(
        recipients=recipient,
        subject=subject,
        message=_(
            "Hello,<br><br>We were unable to process your email attachment for transaction parsing.<br><br>Error: {0}<br><br>Please check the attachment and process it manually if required."
        ).format(error_message),
        attachments=[{"file_url": file_url}],
    )
