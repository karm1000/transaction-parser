import frappe


def enqueue_notification(**kwargs):
    frappe.enqueue(create_notification, **kwargs)


def create_notification(document_type, document_name, subject, message=None):
    notification = frappe.get_doc(
        {
            "doctype": "Notification Log",
            "for_user": frappe.session.user,
            "type": "Alert",
            "document_type": document_type,
            "document_name": document_name,
            "subject": subject,
            "email_content": message,
        }
    )
    notification.insert(ignore_permissions=True)
