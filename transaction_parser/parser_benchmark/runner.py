import tracemalloc
from timeit import default_timer

import frappe

from transaction_parser.transaction_parser.ai_integration.parser import AIParser
from transaction_parser.transaction_parser.controllers import get_controller
from transaction_parser.transaction_parser.utils.file_processor import FileProcessor
from transaction_parser.transaction_parser.utils.pdf_processor import get_pdf_processor


class BenchmarkRunner:
    """
    Wraps the existing Transaction Parser flow to capture
    performance metrics (time, memory, tokens, cost) for benchmarking.

    Flow:
        1. File parsing   → time, memory, extracted content
        2. AI parsing     → time, tokens, cost, AI response
        3. Doc generation → linked document (Sales Order / Purchase Invoice)
    """

    def __init__(self, log_name: str):
        self.log = frappe.get_doc("Parser Benchmark Log", log_name)
        self.dataset = frappe.get_doc("Parser Benchmark Dataset", self.log.dataset)

        # intermediate state shared between steps
        self._file_content = None
        self._ai_content = None
        self._controller = None

    def run(self):
        self.log.status = "Running"
        self.log.ai_model = self.dataset.ai_model
        self.log.pdf_processor = self.dataset.pdf_processor
        self.log.save(ignore_permissions=True)
        frappe.db.commit()

        total_start = default_timer()

        try:
            file_doc = self._get_file_doc()
            self._run_file_parsing(file_doc)
            self._run_ai_parsing(file_doc)
            self._run_document_generation(file_doc)
            self._calculate_cost()

            self.log.status = "Completed"

        except Exception:
            self.log.status = "Failed"
            self.log.error = frappe.get_traceback()

        finally:
            self.log.total_time = round(default_timer() - total_start, 4)
            self.log.save(ignore_permissions=True)
            frappe.db.commit()

        return self.log.name

    # ── helpers ──────────────────────────────────────────────

    def _get_file_doc(self):
        return frappe.get_last_doc("File", filters={"file_url": self.dataset.file})

    def _get_controller(self):
        cls = get_controller(self.dataset.country, self.dataset.transaction_type)
        controller = cls(company=self.dataset.company)
        controller.initialize()
        return controller

    # ── step 1: file parsing ────────────────────────────────

    def _run_file_parsing(self, file_doc):
        pdf_processor = None
        if file_doc.file_type == "PDF" and self.dataset.pdf_processor:
            pdf_processor = get_pdf_processor(self.dataset.pdf_processor)

        tracemalloc.start()
        start = default_timer()
        try:
            content = FileProcessor().get_content(
                file_doc,
                self.dataset.page_limit or None,
                pdf_processor,
            )
        finally:
            self.log.file_parse_time = round(default_timer() - start, 4)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

        self.log.file_parse_memory = round(peak / 1024 / 1024, 2)  # bytes → MB
        self.log.file_content = content
        self._file_content = content

    # ── step 2: AI parsing ──────────────────────────────────

    def _run_ai_parsing(self, file_doc):
        self._controller = self._get_controller()
        self._controller.file = file_doc

        schema = self._controller.get_schema()
        parser = AIParser(self.dataset.ai_model)

        start = default_timer()
        ai_content, response = parser.parse_with_response(
            document_type=self._controller.DOCTYPE,
            document_schema=schema,
            document_data=self._file_content,
            file_doc_name=file_doc.name,
        )
        self.log.ai_parse_time = round(default_timer() - start, 4)

        # token usage
        usage = response.get("usage", {})
        self.log.prompt_tokens = usage.get("prompt_tokens", 0)
        self.log.completion_tokens = usage.get("completion_tokens", 0)
        self.log.total_tokens = usage.get("total_tokens", 0)

        # parsed content
        self.log.ai_response = frappe.as_json(ai_content, indent=2)
        self._ai_content = ai_content

    # ── step 3: document generation ─────────────────────────

    def _run_document_generation(self, file_doc):
        c = self._controller
        c.data = self._ai_content
        c.create_document()
        c.doc.db_set("is_created_by_benchmark", 1)

        self.log.document_type = c.DOCTYPE
        self.log.document_name = c.doc.name

    # ── step 4: cost calculation ────────────────────────────

    def _calculate_cost(self):
        try:
            settings = frappe.get_cached_doc("Parser Benchmark Settings")
        except Exception:
            return

        cost_row = None
        for row in settings.token_costs:
            if row.ai_model == self.dataset.ai_model:
                cost_row = row
                break

        if not cost_row:
            return

        self.log.currency = cost_row.currency
        self.log.input_token_cost = cost_row.input_cost_per_million
        self.log.output_token_cost = cost_row.output_cost_per_million

        prompt = self.log.prompt_tokens or 0
        completion = self.log.completion_tokens or 0

        self.log.input_cost = round(
            prompt * cost_row.input_cost_per_million / 1_000_000, 6
        )
        self.log.output_cost = round(
            completion * cost_row.output_cost_per_million / 1_000_000, 6
        )
        self.log.total_cost = round(self.log.input_cost + self.log.output_cost, 6)
