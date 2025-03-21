import io
import json
import re
from tempfile import TemporaryFile

import frappe
import ocrmypdf
from frappe import _
from pypdf import PdfReader, PdfWriter

from transaction_parser.transaction_parser.document_parser.ai_utils.client import (
    AIClient,
)
from transaction_parser.transaction_parser.document_parser.ai_utils.prompts import (
    get_system_prompt,
    get_user_prompt,
)
from transaction_parser.transaction_parser.document_parser.output_schema_providers import (
    get_output_schema_provider,
)
from transaction_parser.transaction_parser.utils import to_dict
from transaction_parser.transaction_parser.utils.integration_request import SERVICE_NAME


class DocumentParser:
    def __init__(self, settings=None):
        self.settings = settings or frappe.get_cached_doc("Transaction Parser Settings")

    def parse(self, country, doctype, file_url, page_limit=None):
        self.country = country
        self.doctype = doctype
        self.file_url = file_url
        self.page_limit = page_limit

        self.file_doc = None
        self.file = None
        self.document_text = None
        self.output_schema = None
        self.parsed_data = None

        self._get_file()
        self._parse()

        return self.parsed_data

    def _get_file(self):
        self.file_doc = frappe.get_last_doc(
            "File",
            filters={"file_url": self.file_url},
        )

        self._validate_file()

    def _validate_file(self):
        if self.file_doc.file_type != "PDF":
            frappe.throw(_("Only PDF files are supported"))

    def _parse(self):
        response = self._get_saved_response()

        if not response:
            response = self._get_ai_response()

        self.parsed_data = self._get_parsed_data(response)

    def _get_saved_response(self):
        if not self.settings.reuse_previously_parsed_data:
            return

        file_names = self._get_duplicate_file_names()

        filters = {
            "integration_request_service": SERVICE_NAME,
            "status": "Completed",
            "reference_doctype": "File",
            "reference_docname": ["in", file_names],
        }

        parsed_data = frappe.db.get_value(
            "Integration Request",
            filters=filters,
            fieldname="output",
        )

        return to_dict(parsed_data, throw=False)

    def _get_duplicate_file_names(self):
        return frappe.get_all(
            "File",
            filters={"file_url": self.file_url},
            pluck="name",
        )

    def _get_ai_response(self):
        client = AIClient(self.settings)

        client.set_default_log_values(
            reference_doctype="File",
            reference_name=self.file_doc.name,
        )

        return client.get_response(
            messages=self._get_prompts(),
        )

    def _get_prompts(self):
        return (
            self._get_system_prompt(),
            self._get_user_prompt(),
        )

    def _get_system_prompt(self):
        self._get_output_schema()

        return {
            "role": "system",
            "content": get_system_prompt(self.doctype, self.output_schema),
        }

    def _get_output_schema(self):
        schema_provider = get_output_schema_provider(self.country, self.doctype)

        _output_schema = schema_provider(self.settings).get_schema()
        self.output_schema = frappe.as_json(_output_schema)

    def _get_user_prompt(self):
        self._get_document_text()

        return {
            "role": "user",
            "content": get_user_prompt(self.document_text),
        }

    def _get_document_text(self):
        self._get_file_content()
        self._get_required_pages()
        self._apply_ocr()
        self._extract_text()

    def _get_file_content(self):
        self.file = io.BytesIO(self.file_doc.get_content())

    def _get_required_pages(self):
        if not self.page_limit:
            return

        reader = PdfReader(self.file)
        writer = PdfWriter()

        for index, page in enumerate(reader.pages):
            if index >= self.page_limit:
                break

            writer.add_page(page)

        temp_file = TemporaryFile()
        writer.write(temp_file)
        temp_file.seek(0)

        self.file = temp_file

    def _apply_ocr(self):
        # TODO: study impacts of force_ocr and deskew
        try:
            temp_file = TemporaryFile()

            ocrmypdf.ocr(
                input_file=self.file,
                output_file=temp_file,
                force_ocr=True,
                deskew=True,
            )

            self.file = temp_file

        except Exception as e:
            frappe.throw(_(f"OCR failed for {self.file_url}: {e}"))

    def _extract_text(self):
        reader = PdfReader(self.file)

        self.document_text = ""
        for page in reader.pages:
            self.document_text += page.extract_text()

    def _get_parsed_data(self, response):
        # TODO: robust json decoder
        if not response:
            frappe.throw(_("No response received"))

        response_content = (
            response.get("choices", [])[0].get("message", {}).get("content")
        )

        if not response_content:
            frappe.throw(_("No response received"))

        try:
            response_json = to_dict(response_content)

        except json.JSONDecodeError:
            try:
                response_json = to_dict(
                    re.search(r"```json(.*)```", response_content, re.DOTALL).group(1)
                )

            except Exception as e:
                frappe.throw(
                    _(f"Failed to parse response content: {response_json} {e}")
                )

        return response_json
