# Copyright (c) 2026, Resilient Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ParserBenchmarkDataset(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        ai_model: DF.Literal[
            "DeepSeek Chat",
            "DeepSeek Reasoner",
            "OpenAI gpt-4o",
            "OpenAI gpt-4o-mini",
            "OpenAI gpt-5",
            "OpenAI gpt-5-mini",
            "Google Gemini Pro",
            "Google Gemini Flash",
        ]
        company: DF.Link
        country: DF.Literal["India", "Other"]
        enabled: DF.Check
        file: DF.Attach
        naming_series: DF.Literal["Parser-Dataset-"]
        page_limit: DF.Int
        pdf_processor: DF.Literal["OCRMyPDF", "Docling"]
        title: DF.Data
        transaction_type: DF.Literal["Sales Order", "Expense"]
    # end: auto-generated types

    pass


@frappe.whitelist()
def run_benchmark(dataset_name: str):
    """Create a Benchmark Log and enqueue the benchmark run."""
    frappe.has_permission("Parser Benchmark Dataset", "write", throw=True)

    log = frappe.get_doc(
        {
            "doctype": "Parser Benchmark Log",
            "dataset": dataset_name,
            "status": "Queued",
        }
    ).insert(ignore_permissions=True)

    frappe.db.commit()  # Ensure the log is saved before the background job picks it up

    frappe.enqueue(
        _run_benchmark,
        log_name=log.name,
        queue="long",
        now=frappe.conf.developer_mode,
    )

    return log.name


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
