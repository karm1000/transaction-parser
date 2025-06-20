import frappe

from transaction_parser.transaction_parser import _parse


def on_update(doc, method=None):
    if not doc.sent_or_received == "Received" or doc.is_processed_by_transaction_parser:
        return

    settings = frappe.get_cached_doc("Transaction Parser Settings")

    if (
        not settings.enabled
        or not settings.parse_incoming_emails
        # Attachments are not available when the Communication doc is created.
        # Next time the doc is updated, we will check for attachments,
        # and update the flag `is_processed_by_transaction_parser` accordingly.
        or not (attachments := doc.get_attachments())
    ):
        return

    for incoming_email_account in settings.incoming_email_accounts:
        if doc.email_account != incoming_email_account.email_account:
            continue

        for attachment in attachments:
            frappe.enqueue(
                _parse,
                country=frappe.defaults.get_user_default("Country"),
                doctype=incoming_email_account.transaction,
                file_url=attachment.file_url,
                ai_model=settings.default_ai_model,
                queue="long",
            )

    doc.db_set("is_processed_by_transaction_parser", 1)
