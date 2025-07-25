import frappe

from transaction_parser.transaction_parser import _parse

PARTY_TYPE_MAP = {
    "Sales Order": "Customer",
}


def on_update(doc, method=None):
    if doc.communication_type != "Communication" or doc.sent_or_received != "Received":
        return

    settings = frappe.get_cached_doc("Transaction Parser Settings")
    if not (settings.enabled and settings.parse_incoming_emails):
        return

    matched_account = next(
        (
            row
            for row in settings.incoming_email_accounts
            if row.to_email in doc.recipients
        ),
        None,
    )

    if not matched_account:
        return

    # Attachments are not available when the Communication doc is created.
    # Next time the doc is updated, we will check for attachments,
    # and update the flag `is_processed_by_transaction_parser` accordingly.
    attachments = doc.get_attachments()
    if not attachments:
        return

    process_attachments(doc, settings, matched_account, attachments)


def process_attachments(doc, settings, matched_account, attachments):
    party_type = PARTY_TYPE_MAP[matched_account.transaction]
    matched_party = next(
        (
            row.party
            for row in settings.party_emails
            if row.party_type == party_type and row.party_email == doc.sender
        ),
        None,
    )

    for attachment in attachments:
        frappe.enqueue(
            _parse,
            country=frappe.db.get_value("Company", matched_account.company, "country"),
            doctype=matched_account.transaction,
            file_url=attachment.file_url,
            ai_model=settings.default_ai_model,
            user=matched_account.user,
            party=matched_party,
            company=matched_account.company,
            queue="long",
        )
    doc.db_set("is_processed_by_transaction_parser", 1)
