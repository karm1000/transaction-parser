# Copyright (c) 2026, Resilient Tech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

# Maps dataset checkbox fieldnames → model/processor display names
AI_MODEL_FIELD_MAP = {
    "deepseek_chat": "DeepSeek Chat",
    "deepseek_reasoner": "DeepSeek Reasoner",
    "openai_gpt_4o": "OpenAI gpt-4o",
    "openai_gpt_4o_mini": "OpenAI gpt-4o-mini",
    "openai_gpt_5": "OpenAI gpt-5",
    "openai_gpt_5_mini": "OpenAI gpt-5-mini",
    "google_gemini_pro_25": "Google Gemini Pro-2.5",
    "google_gemini_flash_25": "Google Gemini Flash-2.5",
}

PDF_PROCESSOR_FIELD_MAP = {
    "ocrmypdf": "OCRMyPDF",
    "docling": "Docling",
}


class ParserBenchmarkDataset(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        company: DF.Link | None
        country: DF.Literal["India", "Other"]
        deepseek_chat: DF.Check
        deepseek_reasoner: DF.Check
        docling: DF.Check
        enabled: DF.Check
        file: DF.Attach
        google_gemini_flash_25: DF.Check
        google_gemini_pro_25: DF.Check
        naming_series: DF.Literal["PAR-BM-DTS-"]
        ocrmypdf: DF.Check
        openai_gpt_4o: DF.Check
        openai_gpt_4o_mini: DF.Check
        openai_gpt_5: DF.Check
        openai_gpt_5_mini: DF.Check
        page_limit: DF.Int
        party: DF.DynamicLink | None
        party_type: DF.Link | None
        title: DF.Data
        transaction_type: DF.Literal["Sales Order", "Expense"]
    # end: auto-generated types

    def validate(self):
        self.file_doc = frappe.get_last_doc("File", filters={"file_url": self.file})
        self.validate_file_type()
        self.validate_selected_models()
        self.validate_selected_processors()

    def validate_file_type(self):
        if self.file_doc.file_type not in ["PDF", "CSV", "XLSX", "XLS"]:
            frappe.throw(
                _("Unsupported file type: {0}").format(self.file_doc.file_type)
            )

    def validate_selected_models(self):
        if not self.get_selected_models():
            frappe.throw(_("Please select at least one AI Model."))

    def validate_selected_processors(self):
        if self.file_doc.file_type != "PDF":
            return

        if not self.get_selected_processors():
            frappe.throw(_("Please select at least one PDF Processor."))

    def get_selected_models(self) -> list[str]:
        """Return list of selected AI model names."""
        return [label for field, label in AI_MODEL_FIELD_MAP.items() if self.get(field)]

    def get_selected_processors(self) -> list[str]:
        """Return list of selected PDF processor names."""
        return [
            label for field, label in PDF_PROCESSOR_FIELD_MAP.items() if self.get(field)
        ]


@frappe.whitelist()
def run_benchmark(dataset_name: str):
    """Create Benchmark Logs for each model x processor combo and enqueue runs."""
    frappe.has_permission("Parser Benchmark Dataset", "write", throw=True)

    dataset = frappe.get_doc("Parser Benchmark Dataset", dataset_name)
    log_names = _create_and_enqueue_logs(dataset)

    if not log_names:
        frappe.throw(_("No model/processor combinations selected."))

    return log_names


def _create_and_enqueue_logs(dataset) -> list[str]:
    """Create one log per model x processor combo and enqueue each for background execution."""
    log_names = []
    processors = dataset.get_selected_processors() or [None]

    for ai_model in dataset.get_selected_models():
        for pdf_processor in processors:
            log = frappe.get_doc(
                {
                    "doctype": "Parser Benchmark Log",
                    "dataset": dataset.name,
                    "status": "Queued",
                    "ai_model": ai_model,
                    "pdf_processor": pdf_processor,
                    "transaction_type": dataset.transaction_type,
                    "country": dataset.country,
                    "company": dataset.company,
                    "party_type": dataset.party_type,
                    "party": dataset.party,
                    "page_limit": dataset.page_limit,
                }
            ).insert(ignore_permissions=True)

            log_names.append(log.name)

    frappe.db.commit()

    for log_name in log_names:
        frappe.enqueue(
            _run_benchmark,
            log_name=log_name,
            queue="long",
            # now=frappe.conf.developer_mode,
        )

    return log_names


def _run_benchmark(log_name: str):
    from transaction_parser.parser_benchmark.runner import BenchmarkRunner

    BenchmarkRunner(log_name).run()


@frappe.whitelist()
def get_pdf_processors():
    frappe.has_permission("Parser Benchmark Dataset", "write", throw=True)

    from transaction_parser.transaction_parser.utils.pdf_processor import (
        get_available_pdf_processors,
    )

    return get_available_pdf_processors()
