import frappe


def enqueue_notification(**kwargs):
    frappe.enqueue(
        "transaction_parser.transaction_parser.utils.notification.create_notification",
        **kwargs,
    )


def create_notification(document_type, document_name, subject):
    notification = frappe.get_doc(
        {
            "doctype": "Notification Log",
            "for_user": frappe.session.user,
            "type": "Alert",
            "document_type": document_type,
            "document_name": document_name,
            "subject": subject,
        }
    )
    notification.insert()
