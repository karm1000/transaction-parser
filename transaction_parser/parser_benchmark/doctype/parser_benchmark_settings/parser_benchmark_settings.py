# Copyright (c) 2026, Resilient Tech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

WEEKDAY_FIELDS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


class ParserBenchmarkSettings(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        from transaction_parser.parser_benchmark.doctype.parser_benchmark_key_weight.parser_benchmark_key_weight import (
            ParserBenchmarkKeyWeight,
        )
        from transaction_parser.parser_benchmark.doctype.parser_benchmark_token_cost.parser_benchmark_token_cost import (
            ParserBenchmarkTokenCost,
        )

        enabled: DF.Check
        friday: DF.Check
        key_weights: DF.Table[ParserBenchmarkKeyWeight]
        monday: DF.Check
        saturday: DF.Check
        sunday: DF.Check
        thursday: DF.Check
        token_costs: DF.Table[ParserBenchmarkTokenCost]
        tuesday: DF.Check
        wednesday: DF.Check
    # end: auto-generated types

    def validate(self):
        self.validate_wights()

    def validate_wights(self):
        if not self.key_weights:
            return

        seen_keys = set()
        for row in self.key_weights:
            if row.key in seen_keys:
                frappe.throw(
                    _("Duplicate key '{0}' in Key Weights row {1}").format(
                        row.key, row.idx
                    )
                )
            seen_keys.add(row.key)

    def is_scheduled_today(self) -> bool:
        """Check if today's weekday is enabled in the schedule."""
        today_index = getdate().weekday()  # 0 = Monday
        return bool(self.get(WEEKDAY_FIELDS[today_index]))


def run_scheduled_benchmarks():
    """Scheduled job: runs all enabled datasets if today is a scheduled day."""
    from transaction_parser.parser_benchmark.doctype.parser_benchmark_dataset.parser_benchmark_dataset import (
        create_and_enqueue_benchmark_logs,
    )

    settings: ParserBenchmarkSettings = frappe.get_cached_doc(
        "Parser Benchmark Settings"
    )

    if not settings.enabled or not settings.is_scheduled_today():
        return

    datasets = frappe.get_all(
        "Parser Benchmark Dataset",
        filters={"enabled": 1, "docstatus": 1},
        pluck="name",
    )

    for dataset_name in datasets:
        try:
            create_and_enqueue_benchmark_logs(dataset_name)
        except Exception:
            frappe.log_error(
                title=f"Failed to enqueue benchmark for dataset {dataset_name}",
                message=frappe.get_traceback(),
            )
