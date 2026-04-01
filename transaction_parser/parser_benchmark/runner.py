import tracemalloc
from timeit import default_timer

import frappe
from frappe import _
from frappe.core.doctype.file.file import File
from frappe.utils import cint, flt

from transaction_parser.parser_benchmark.doctype.parser_benchmark_dataset.parser_benchmark_dataset import (
    ParserBenchmarkDataset,
)
from transaction_parser.parser_benchmark.doctype.parser_benchmark_log.parser_benchmark_log import (
    ParserBenchmarkLog,
)
from transaction_parser.parser_benchmark.doctype.parser_benchmark_settings.parser_benchmark_settings import (
    ParserBenchmarkSettings,
)
from transaction_parser.transaction_parser.ai_integration.parser import AIParser
from transaction_parser.transaction_parser.controllers import get_controller
from transaction_parser.transaction_parser.controllers.transaction import Transaction
from transaction_parser.transaction_parser.utils.file_processor import FileProcessor
from transaction_parser.transaction_parser.utils.pdf_processor import get_pdf_processor


class BenchmarkRunner:
    """
    Runs a single benchmark for one AI model + PDF processor combination.

    Flow:
        1. File parsing   → time, memory, extracted content
        2. AI parsing     → time, tokens, cost, AI response
    """

    def __init__(
        self,
        log_name: str,
        dataset: ParserBenchmarkDataset | None = None,
        settings: ParserBenchmarkSettings | None = None,
    ):
        self.log: ParserBenchmarkLog = frappe.get_doc("Parser Benchmark Log", log_name)
        self.dataset: ParserBenchmarkDataset = dataset or frappe.get_cached_doc(
            "Parser Benchmark Dataset", self.log.dataset
        )
        self.settings: ParserBenchmarkSettings = settings or frappe.get_cached_doc(
            "Parser Benchmark Settings"
        )
        self.precision = 6  # to get 1-millionth of a token cost

        # for accuracy score
        self.significant_digits = cint(frappe.db.get_default("float_precision")) or 2

    def run(self):
        self.log.status = "Running"
        self.log.currency = "USD"
        self.log.save(ignore_permissions=True)
        frappe.db.commit()  # nosemgrep -- persist "Running" status before long-running benchmark

        total_start = default_timer()

        try:
            file_docs: list[File] = self._get_file_docs()
            self.controller: Transaction = self._get_controller(file_docs[0])

            file_content = self._run_file_parsing(file_docs)
            ai_content = self._run_ai_parsing(file_content, file_docs[0].name)
            self._calculate_cost()
            self._score_response(ai_content)

            self.log.status = "Completed"

        except Exception:
            self.log.status = "Failed"
            self.log.error = frappe.get_traceback()

        finally:
            self.log.total_time = flt(default_timer() - total_start, self.precision)
            self.log.save(ignore_permissions=True)
            frappe.db.commit()  # nosemgrep -- persist final results inside background job

        return self.log.name

    # ── helpers ──────────────────────────────────────────────

    def _get_file_docs(self) -> list[File]:
        file_docs = self.dataset.get_file_docs()
        if not file_docs:
            frappe.throw(_("No files in dataset {0}").format(self.dataset.name))
        return file_docs

    def _get_controller(self, file_doc: File) -> Transaction:
        ds = self.dataset
        cls = get_controller(ds.country, ds.transaction_type)

        controller: Transaction = cls(company=ds.company, party=ds.party)
        controller.initialize()
        controller.file = file_doc
        controller.ai_model = self.log.ai_model

        return controller

    def _get_cost_row(self):
        for row in self.settings.token_costs:
            if row.ai_model == self.log.ai_model:
                return row

        return None

    # ── step 1: file parsing ────────────────────────────────

    def _run_file_parsing(self, file_docs: list[File]) -> str:
        # to prevent stopping an already running tracemalloc instance
        was_tracing = tracemalloc.is_tracing()
        if not was_tracing:
            tracemalloc.start()

        start = default_timer()
        try:
            contents = []
            for file_doc in file_docs:
                pdf_processor = None
                if file_doc.file_type == "PDF" and self.log.pdf_processor:
                    pdf_processor = get_pdf_processor(self.log.pdf_processor)

                content = FileProcessor().get_content(
                    file_doc,
                    self.dataset.page_limit or None,
                    pdf_processor,
                )
                contents.append(content)

            combined = (
                "\n\n--- Document Separator ---\n\n".join(contents)
                if len(contents) > 1
                else contents[0]
            )
        finally:
            self.log.file_parse_time = flt(default_timer() - start, self.precision)
            _, peak = tracemalloc.get_traced_memory()
            if not was_tracing:
                tracemalloc.stop()
            self.log.file_parse_memory = flt(
                peak / 1024 / 1024, self.precision
            )  # bytes → MB

        self.log.file_content = combined
        return combined

    # ── step 2: AI parsing ──────────────────────────────────

    def _run_ai_parsing(self, file_content: str, file_name: str) -> dict:
        parser = AIParser(self.log.ai_model)

        start = default_timer()
        ai_content = parser.parse(
            document_type=self.controller.DOCTYPE,
            document_schema=self.controller.get_schema(),
            document_data=file_content,
            file_doc_name=file_name,
            company=self.dataset.company,
        )
        self.log.ai_parse_time = flt(default_timer() - start, self.precision)

        usage = parser.ai_response.get("usage", {})
        self.log.prompt_tokens = usage.get("prompt_tokens", 0)
        self.log.completion_tokens = usage.get("completion_tokens", 0)
        self.log.total_tokens = usage.get("total_tokens", 0)
        self.log.ai_response = frappe.as_json(ai_content, indent=2)

        return ai_content

    # ── step 3: cost calculation ────────────────────────────

    def _calculate_cost(self):
        cost_row = self._get_cost_row()
        if not cost_row:
            return

        self.log.currency = cost_row.currency
        self.log.input_token_cost = cost_row.input_cost_per_million
        self.log.output_token_cost = cost_row.output_cost_per_million

        prompt = self.log.prompt_tokens or 0
        completion = self.log.completion_tokens or 0

        self.log.input_cost = flt(
            prompt * cost_row.input_cost_per_million / 1_000_000, self.precision
        )
        self.log.output_cost = flt(
            completion * cost_row.output_cost_per_million / 1_000_000, self.precision
        )
        self.log.total_cost = flt(
            self.log.input_cost + self.log.output_cost, self.precision
        )

    # ── step 4: accuracy scoring ─────────────────────────────

    def _score_response(self, ai_content: dict):
        from transaction_parser.parser_benchmark.scorer import score_response

        expected_fields = self.dataset.expected_fields
        if not expected_fields:
            return

        weights = self._get_key_weights()

        result = score_response(
            expected_fields=[
                {"key": row.key, "expected_json": row.expected_json}
                for row in expected_fields
            ],
            actual=ai_content,
            weights=weights,
            precision=self.significant_digits,
        )

        self.log.accuracy_score = result["overall_accuracy"]

        for detail in result["details"]:
            self.log.append(
                "score_details",
                {
                    "key": detail["key"],
                    "matched": detail["matched"],
                    "total": detail["total"],
                    "accuracy": detail["accuracy"],
                    "mismatches": frappe.as_json(detail["mismatches"], indent=2)
                    if detail["mismatches"]
                    else None,
                },
            )

    def _get_key_weights(self) -> dict[str, float]:
        """Load key weights from Parser Benchmark Settings."""
        return {row.key: row.weight for row in (self.settings.key_weights or [])}
