import re

import frappe
from frappe import _
from openai import OpenAI

from transaction_parser.transaction_parser.ai_integration.models import MODELS
from transaction_parser.transaction_parser.ai_integration.prompts import (
    get_system_prompt,
    get_user_prompt,
)
from transaction_parser.transaction_parser.utils import is_enabled, to_dict
from transaction_parser.transaction_parser.utils.integration_request import (
    enqueue_integration_request,
)


class AIParser:
    def __init__(self, model=None, settings=None):
        self.settings = settings or frappe.get_cached_doc("Transaction Parser Settings")

        is_enabled(self.settings)

        self.model = MODELS.get(model) or MODELS.get(self.settings.default_ai_model)
        if not self.model:
            frappe.throw(_(f"AI Model: {model} not found"))

    def parse(self, document_type, document_schema, document_data, file_doc_name):
        system_prompt = get_system_prompt(document_schema)
        user_prompt = get_user_prompt(document_type, document_data)
        messages = (
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        )

        return self.get_content(
            self.send_message(messages=messages, file_doc_name=file_doc_name)
        )

    def send_message(self, messages, file_doc_name):
        log = frappe._dict(
            {
                "reference_doctype": "File",
                "reference_name": file_doc_name,
                "url": self.model.base_url,
            }
        )

        try:
            with OpenAI(
                api_key=self.get_api_key(),
                base_url=self.model.base_url,
            ) as client:
                response = client.chat.completions.create(
                    model=self.model.name,
                    messages=messages,
                    response_format={"type": self.model.response_format},
                    stream=False,
                    temperature=0.7,
                )

            log.request_id = response.id

            response = response.to_dict()
            log.output = response

            response = self.get_response(response)
            log.output = response

            return response

        except Exception as e:
            log.error = str(e)
            raise e

        finally:
            enqueue_integration_request(**log)

    def get_api_key(self):
        for key in self.settings.api_keys:
            if key.service_provider == self.model.service_provider:
                return key.get_password("api_key")

    def get_response(self, response):
        if not response:
            frappe.throw(_("No response received"))

        response["choices"][0]["message"]["content"] = self.get_content(response)

        return response

    def get_content(self, response):
        content = response["choices"][0]["message"]["content"]

        if not isinstance(content, str):
            return content

        return self._get_content(content)

    def _get_content(self, content):
        # TODO: robust json decoder
        if not content:
            frappe.throw(_("No response content received"))

        try:
            return to_dict(content)

        except Exception:
            try:
                return to_dict(
                    re.search(r"```json(.*)```", content, re.DOTALL).group(1)
                )

            except Exception as e:
                frappe.throw(_(f"Failed to parse response content: {e}"))
