import frappe

from transaction_parser.transaction_parser.ai_integration.client import (
    AIClient,
    get_content,
)
from transaction_parser.transaction_parser.ai_integration.prompts import (
    get_system_prompt,
    get_user_prompt,
)


class AIParser:
    def __init__(self, settings=None):
        self.settings = settings or frappe.get_cached_doc("Transaction Parser Settings")

    def parse(self, doctype, schema, file_doc_name, data):
        client = AIClient(self.settings)

        client.set_default_log_values(
            reference_doctype="File",
            reference_name=file_doc_name,
        )

        messages = (
            self._get_system_prompt(doctype, schema),
            self._get_user_prompt(data),
        )

        return client.send_message(messages=messages)

    def _get_system_prompt(self, doctype, schema):
        return {
            "role": "system",
            "content": get_system_prompt(doctype, schema),
        }

    def _get_user_prompt(self, file_data):
        return {
            "role": "user",
            "content": get_user_prompt(file_data),
        }
