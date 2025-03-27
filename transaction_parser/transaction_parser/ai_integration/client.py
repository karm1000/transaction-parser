import re

import frappe
from frappe import _
from openai import OpenAI

from transaction_parser.transaction_parser.ai_integration.models import MODELS
from transaction_parser.transaction_parser.utils import is_enabled, to_dict
from transaction_parser.transaction_parser.utils.integration_request import (
    enqueue_integration_request,
)


class AIClient:
    def __init__(self, settings=None):
        self.settings = settings or frappe.get_cached_doc("Transaction Parser Settings")

        is_enabled(self.settings)

        self.model = MODELS.get(self.settings.ai_model)
        self._default_log_values = {}

    def set_default_log_values(self, **kwargs):
        self._default_log_values = {**kwargs}

    def send_message(self, **kwargs):
        return self._make_request(**kwargs)

    def _make_request(self, **kwargs):
        log = frappe._dict(
            {
                **self._default_log_values,
                "url": self.model.base_url,
            }
        )

        request_args = {
            **kwargs,
            "model": self.model.name,
            "stream": False,
            "response_format": {
                "type": self.model.response_format,
            },
        }

        try:
            with OpenAI(
                api_key=(
                    self.settings.api_key and self.settings.get_password("api_key")
                ),
                base_url=self.model.base_url,
            ) as client:
                response = client.chat.completions.create(**request_args)

            log.request_id = response.id

            response = response.to_dict()
            log.output = response

            response = get_response(response)
            log.output = response

            return response

        except Exception as e:
            log.error = str(e)
            raise e

        finally:
            enqueue_integration_request(**log)


def get_response(response):
    if not response:
        frappe.throw(_("No response received"))

    response["choices"][0]["message"]["content"] = get_content(response)

    return response


def get_content(response):
    content = response["choices"][0]["message"]["content"]

    if not isinstance(content, str):
        return content

    return _get_content(content)


def _get_content(content):
    # TODO: robust json decoder
    if not content:
        frappe.throw(_("No response content received"))

    try:
        return to_dict(content)

    except Exception:
        try:
            return to_dict(re.search(r"```json(.*)```", content, re.DOTALL).group(1))

        except Exception as e:
            frappe.throw(_(f"Failed to parse response content: {content} {e}"))
