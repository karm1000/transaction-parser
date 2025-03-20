import frappe
from openai import OpenAI

from transaction_parser.transaction_parser.document_parser.ai_utils.models import MODELS
from transaction_parser.transaction_parser.utils import is_enabled
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

    def get_response(self, **kwargs):
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
                response_json = response.to_dict()

                log.request_id = response.id
                log.output = response_json

                return response_json

        except Exception as e:
            log.error = str(e)
            raise e

        finally:
            enqueue_integration_request(**log)
