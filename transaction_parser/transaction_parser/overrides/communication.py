import frappe
from frappe import _

from transaction_parser.transaction_parser import _parse
from transaction_parser.transaction_parser.utils.notification import (
    enqueue_notification,
)


def on_communication_update(doc, method=None):
    if not doc.sent_or_received == "Received":
        return

    settings = frappe.get_cached_doc("Transaction Parser Settings")
    if not (settings.enabled and settings.parse_incoming_emails):
        return

    attachments = doc.get_attachments()
    # Attachments are not available when the Communication doc is created.
    # Next time the doc is updated, we will check for attachments,
    # and update the flag `is_processed_by_transaction_parser` accordingly.
    if not attachments:
        return

    process_attachments(doc, settings, attachments)


def process_attachments(doc, settings, attachments):
    matched_account = next(
        (
            row
            for row in settings.incoming_email_accounts
            if row.to_email in doc.recipients
        ),
        None,
    )

    if not matched_account:
        # TODO: Better error message
        error_log = frappe.log_error(
            title=_("Cannot Parse Transaction"),
            message=_("No matching To Email found in Transaction Parser Settings."),
            reference_doctype=doc.doctype,
            reference_name=doc.name,
        )

        enqueue_notification(
            document_type=error_log.doctype,
            document_name=error_log.name,
            subject=_("Failed to Parse Transaction from {0}").format(doc.name),
        )
        return

    party = next(
        (row.party for row in settings.party_emails if row.party_email == doc.sender),
        None,
    )

    for attachment in attachments:
        frappe.enqueue(
            _parse,
            country=frappe.defaults.get_user_default("Country"),
            doctype=matched_account.transaction,
            file_url=attachment.file_url,
            ai_model=settings.default_ai_model,
            user=matched_account.user,
            party=party,
            default_company=matched_account.company,
            queue="long",
        )
    doc.db_set("is_processed_by_transaction_parser", 1)
