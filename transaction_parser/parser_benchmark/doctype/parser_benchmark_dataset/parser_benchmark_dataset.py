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
