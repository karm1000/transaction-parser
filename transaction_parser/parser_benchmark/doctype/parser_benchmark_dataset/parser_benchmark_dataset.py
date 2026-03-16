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

        ai_model: DF.Select
        company: DF.Link
        country: DF.Select
        enabled: DF.Check
        file: DF.Attach
        page_limit: DF.Int
        pdf_processor: DF.Select | None
        title: DF.Data
        transaction_type: DF.Select
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

    frappe.db.commit() # Ensure the log is saved before the background job picks it up

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
