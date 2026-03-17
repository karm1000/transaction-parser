import tracemalloc
from timeit import default_timer

import frappe
from frappe.utils import cint, flt

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
        self.precision = cint(frappe.db.get_default("float_precision")) or 3

    def run(self):
        self.log.status = "Running"
        self.log.ai_model = self.dataset.ai_model
        self.log.pdf_processor = self.dataset.pdf_processor
        self.log.save(ignore_permissions=True)
        frappe.db.commit()  # persist "Running" status before the long background job starts

        total_start = default_timer()

        try:
            file_doc = self._get_file_doc()
            controller = self._get_controller(file_doc)

            file_content = self._run_file_parsing(file_doc)
            ai_content = self._run_ai_parsing(controller, file_content, file_doc)
            self._run_document_generation(controller, ai_content)
            self._calculate_cost()

            self.log.status = "Completed"

        except Exception:
            self.log.status = "Failed"
            self.log.error = frappe.get_traceback()

        finally:
            self.log.total_time = flt(default_timer() - total_start, self.precision)
            self.log.save(ignore_permissions=True)
            frappe.db.commit()  # background jobs don't auto-commit; persist final results

        return self.log.name

    # ── helpers ──────────────────────────────────────────────

    def _get_file_doc(self):
        return frappe.get_last_doc("File", filters={"file_url": self.dataset.file})

    def _get_controller(self, file_doc):
        ds = self.dataset
        cls = get_controller(ds.country, ds.transaction_type)

        controller = cls(company=ds.company)
        controller.initialize()
        controller.file = file_doc

        return controller

    def _get_cost_row(self):
        try:
            settings = frappe.get_cached_doc("Parser Benchmark Settings")
        except Exception:
            return None

        for row in settings.token_costs:
            if row.ai_model == self.dataset.ai_model:
                return row

        return None

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
            self.log.file_parse_time = flt(default_timer() - start, self.precision)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

        self.log.file_parse_memory = flt(
            peak / 1024 / 1024, self.precision
        )  # bytes → MB
        self.log.file_content = content
        return content

    # ── step 2: AI parsing ──────────────────────────────────

    def _run_ai_parsing(self, controller, file_content, file_doc):
        parser = AIParser(self.dataset.ai_model)

        start = default_timer()
        ai_content = parser.parse(
            document_type=controller.DOCTYPE,
            document_schema=controller.get_schema(),
            document_data=file_content,
            file_doc_name=file_doc.name,
        )
        self.log.ai_parse_time = flt(default_timer() - start, self.precision)

        usage = parser.ai_response.get("usage", {})
        self.log.prompt_tokens = usage.get("prompt_tokens", 0)
        self.log.completion_tokens = usage.get("completion_tokens", 0)
        self.log.total_tokens = usage.get("total_tokens", 0)
        self.log.ai_response = frappe.as_json(ai_content, indent=2)

        return ai_content

    # ── step 3: document generation ─────────────────────────

    def _run_document_generation(self, controller, ai_content):
        controller.data = ai_content
        controller.create_document()
        controller.doc.db_set("is_created_by_benchmark", 1)

        self.log.document_type = controller.DOCTYPE
        self.log.document_name = controller.doc.name

    # ── step 4: cost calculation ────────────────────────────

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
