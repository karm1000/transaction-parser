# Copyright (c) 2026, Resilient Tech and contributors
# For license information, please see license.txt

# TODO: Need to refactor and Test
# TODO: Need to add, what does getting mismatched!!!
# TODO: Need to create a other report as well like comparing with commits

from collections import defaultdict
from enum import StrEnum

import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce

PARTY_TYPE_MAP = {
    "Sales Order": "Customer",
    "Expense": "Supplier",
}

# Sorting order for child rows within each party group
_AI_MODEL_ORDER = {
    "OpenAI gpt-5": 0,
    "OpenAI gpt-5-mini": 1,
    "OpenAI gpt-4o": 2,
    "OpenAI gpt-4o-mini": 3,
    "Google Gemini Pro-2.5": 4,
    "Google Gemini Flash-2.5": 5,
    "DeepSeek Reasoner": 6,
    "DeepSeek Chat": 7,
}

_PDF_PROCESSOR_ORDER = {
    "OCRMyPDF": 0,
    "Docling": 1,
}


class Col(StrEnum):
    """Column fieldnames — single source of truth for the report."""

    PARTY = "party"
    PARTY_NAME = "party_name"
    ACCURACY_SCORE = "accuracy_score"
    AI_MODEL = "ai_model"
    PDF_PROCESSOR = "pdf_processor"
    FILE_PARSE_TIME = "file_parse_time"
    FILE_PARSE_MEMORY = "file_parse_memory"
    AI_PARSE_TIME = "ai_parse_time"
    TOTAL_TIME = "total_time"
    TOTAL_COST = "total_cost"
    PROMPT_TOKENS = "prompt_tokens"
    COMPLETION_TOKENS = "completion_tokens"
    TOTAL_TOKENS = "total_tokens"
    CURRENCY = "currency"
    DATASET = "dataset"
    RUN_COUNT = "run_count"
    KEY_SCORES = "key_scores"
    LOG_NAMES = "log_names"


# Fields averaged in party-group summary rows
_AVG_FIELDS = (
    Col.ACCURACY_SCORE,
    Col.FILE_PARSE_TIME,
    Col.FILE_PARSE_MEMORY,
    Col.AI_PARSE_TIME,
    Col.TOTAL_TIME,
    Col.PROMPT_TOKENS,
    Col.COMPLETION_TOKENS,
    Col.TOTAL_TOKENS,
)

# Fields summed in party-group summary rows
_SUM_FIELDS = (Col.TOTAL_COST,)


def execute(filters=None):
    filters = frappe._dict(filters or {})
    return AccuracyAnalysisReport(filters).run()


class AccuracyAnalysisReport:
    def __init__(self, filters: frappe._dict):
        self.filters = filters
        self._set_party_type()
        self.group_by_party = True

    def run(self):
        logs = self._fetch_logs()
        score_details_map = self._fetch_score_details([r.log_name for r in logs])

        self.data = [self._build_row(r, score_details_map) for r in logs]
        self._aggregate_by_config()

        if self.group_by_party:
            self._group_by_party()

        # discover all unique key names for dynamic columns
        all_keys = dict.fromkeys(
            k for row in self.data for k in (row.get("_key_accuracies") or {})
        )

        # strip internal keys before sending to client
        for row in self.data:
            row.pop("_key_accuracies", None)

        return self._get_columns(list(all_keys)), self.data

    # ── Columns ──────────────────────────────────────────────────────

    def _get_columns(self, key_names=None):
        columns = [
            {
                "fieldname": Col.PARTY,
                "label": _("Party"),
                "fieldtype": "Data",
                "width": 200,
            },
            {
                "fieldname": Col.PARTY_NAME,
                "label": _("Party Name"),
                "fieldtype": "Data",
                "width": 200,
            },
            {
                "fieldname": Col.DATASET,
                "label": _("Dataset"),
                "fieldtype": "Link",
                "options": "Parser Benchmark Dataset",
                "width": 160,
            },
            {
                "fieldname": Col.RUN_COUNT,
                "label": _("Runs"),
                "fieldtype": "Int",
                "width": 70,
            },
            {
                "fieldname": Col.ACCURACY_SCORE,
                "label": _("Accuracy (%)"),
                "fieldtype": "Percent",
                "width": 120,
            },
            {
                "fieldname": Col.AI_MODEL,
                "label": _("AI Model"),
                "fieldtype": "Data",
                "width": 180,
            },
            {
                "fieldname": Col.PDF_PROCESSOR,
                "label": _("Processor"),
                "fieldtype": "Data",
                "width": 110,
            },
            {
                "fieldname": Col.FILE_PARSE_TIME,
                "label": _("File Parse (s)"),
                "fieldtype": "Float",
                "width": 120,
                "precision": 2,
            },
            {
                "fieldname": Col.FILE_PARSE_MEMORY,
                "label": _("Memory (MB)"),
                "fieldtype": "Float",
                "width": 110,
                "precision": 2,
            },
            {
                "fieldname": Col.AI_PARSE_TIME,
                "label": _("AI Parse (s)"),
                "fieldtype": "Float",
                "width": 110,
                "precision": 2,
            },
            {
                "fieldname": Col.TOTAL_TIME,
                "label": _("Total (s)"),
                "fieldtype": "Float",
                "width": 100,
                "precision": 2,
            },
            {
                "fieldname": Col.TOTAL_COST,
                "label": _("Total Cost"),
                "fieldtype": "Currency",
                "width": 110,
                "options": Col.CURRENCY,
            },
            {
                "fieldname": Col.PROMPT_TOKENS,
                "label": _("Prompt Tokens"),
                "fieldtype": "Int",
                "width": 120,
            },
            {
                "fieldname": Col.COMPLETION_TOKENS,
                "label": _("Compl. Tokens"),
                "fieldtype": "Int",
                "width": 120,
            },
            {
                "fieldname": Col.TOTAL_TOKENS,
                "label": _("Total Tokens"),
                "fieldtype": "Int",
                "width": 110,
            },
        ]

        # dynamic per-key accuracy columns
        for key in key_names or []:
            columns.append(
                {
                    "fieldname": f"key_{key}",
                    "label": _(key.replace("_", " ").title() + " (%)"),
                    "fieldtype": "Percent",
                    "width": 120,
                }
            )

        columns.append(
            {
                "fieldname": Col.LOG_NAMES,
                "label": _("Logs"),
                "fieldtype": "Data",
                "width": 100,
            }
        )

        return columns

    # ── Query ─────────────────────────────────────────────────────

    def _fetch_logs(self):
        log = frappe.qb.DocType("Parser Benchmark Log")
        ds = frappe.qb.DocType("Parser Benchmark Dataset")
        cust = frappe.qb.DocType("Customer")
        supp = frappe.qb.DocType("Supplier")

        query = (
            frappe.qb.from_(log)
            .join(ds)
            .on(log.dataset == ds.name)
            .left_join(cust)
            .on((ds.party_type == "Customer") & (ds.party == cust.name))
            .left_join(supp)
            .on((ds.party_type == "Supplier") & (ds.party == supp.name))
            .select(
                log.name.as_("log_name"),
                log.ai_model,
                log.pdf_processor,
                log.accuracy_score,
                log.file_parse_time,
                log.file_parse_memory,
                log.ai_parse_time,
                log.total_time,
                log.total_cost,
                log.prompt_tokens,
                log.completion_tokens,
                log.total_tokens,
                log.currency,
                log.dataset,
                ds.party,
                Coalesce(cust.customer_name, supp.supplier_name, ds.party).as_(
                    "party_name"
                ),
            )
            .where(log.status == "Completed")
            .where(ds.docstatus == 1)
            .orderby(ds.party, log.ai_model)
        )

        if not self.filters.get("include_disabled_datasets"):
            query = query.where(ds.enabled == 1)

        if self.filters.get("is_multiple_files"):
            query = query.where(ds.is_multiple_files == 1)

        # exact-match filters
        for column, key in (
            (ds.company, "company"),
            (ds.transaction_type, "transaction_type"),
            (ds.party_type, "party_type"),
            (ds.party, "party"),
        ):
            if self.filters.get(key):
                query = query.where(column == self.filters[key])

        # multi-select IN filters
        for column, key in (
            (log.ai_model, "ai_model"),
            (log.pdf_processor, "pdf_processor"),
        ):
            values = self.filters.get(key)
            if values:
                items = values if isinstance(values, list) else [values]
                query = query.where(column.isin(items))

        return query.run(as_dict=True)

    def _fetch_score_details(self, log_names: list[str]) -> dict[str, list[dict]]:
        """Fetch score_details child rows for all logs at once."""
        if not log_names:
            return {}

        sd = frappe.qb.DocType("Parser Benchmark Score Detail")
        rows = (
            frappe.qb.from_(sd)
            .select(sd.parent, sd.key, sd.matched, sd.total, sd.accuracy)
            .where(sd.parent.isin(log_names))
            .orderby(sd.idx)
            .run(as_dict=True)
        )

        details_map: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            details_map[row.parent].append(row)

        return details_map

    # ── Helpers ──────────────────────────────────────────────────────

    def _set_party_type(self):
        """Derive party_type from transaction_type when not explicitly set."""
        transaction_type = self.filters.get("transaction_type")
        if transaction_type and not self.filters.get("party_type"):
            self.filters["party_type"] = PARTY_TYPE_MAP.get(transaction_type)

    def _build_row(self, r, score_details_map):
        """Build a single detail row from a log record."""
        details = score_details_map.get(r.log_name, [])
        key_accuracies = {d["key"]: d["accuracy"] for d in details}

        row = {
            Col.PARTY: r.party or _("No Party"),
            Col.PARTY_NAME: r.party_name or "",
            Col.ACCURACY_SCORE: r.accuracy_score,
            Col.AI_MODEL: r.ai_model,
            Col.PDF_PROCESSOR: r.pdf_processor,
            Col.DATASET: r.dataset,
            Col.FILE_PARSE_TIME: r.file_parse_time,
            Col.FILE_PARSE_MEMORY: r.file_parse_memory,
            Col.AI_PARSE_TIME: r.ai_parse_time,
            Col.TOTAL_TIME: r.total_time,
            Col.TOTAL_COST: r.total_cost,
            Col.PROMPT_TOKENS: r.prompt_tokens,
            Col.COMPLETION_TOKENS: r.completion_tokens,
            Col.TOTAL_TOKENS: r.total_tokens,
            Col.CURRENCY: r.currency,
            Col.LOG_NAMES: r.log_name,
            "_key_accuracies": key_accuracies,
        }

        # per-key accuracy as separate fields
        for k, v in key_accuracies.items():
            row[f"key_{k}"] = v

        return row

    # ── Aggregation ──────────────────────────────────────────────────

    def _aggregate_by_config(self):
        """Collapse multiple runs of the same config into one averaged row."""
        if not self.data:
            return

        groups: dict[tuple, list[dict]] = defaultdict(list)
        for row in self.data:
            key = (
                row.get(Col.DATASET),
                row.get(Col.AI_MODEL),
                row.get(Col.PDF_PROCESSOR) or "",
            )
            groups[key].append(row)

        aggregated = []
        for _key, rows in groups.items():
            count = len(rows)
            agg = {
                Col.PARTY: rows[0].get(Col.PARTY),
                Col.PARTY_NAME: rows[0].get(Col.PARTY_NAME),
                Col.AI_MODEL: rows[0].get(Col.AI_MODEL),
                Col.PDF_PROCESSOR: rows[0].get(Col.PDF_PROCESSOR),
                Col.CURRENCY: rows[0].get(Col.CURRENCY),
                Col.RUN_COUNT: count,
            }

            agg[Col.DATASET] = rows[0].get(Col.DATASET, "")

            # collect all log names used
            agg[Col.LOG_NAMES] = ",".join(
                r.get(Col.LOG_NAMES) for r in rows if r.get(Col.LOG_NAMES)
            )

            for field in _AVG_FIELDS:
                vals = [r.get(field) or 0 for r in rows]
                agg[field] = round(sum(vals) / count, 2) if count else 0

            for field in _SUM_FIELDS:
                agg[field] = round(sum(r.get(field) or 0 for r in rows) / count, 6)

            # aggregate per-key accuracies
            all_key_accs: dict[str, list[float]] = defaultdict(list)
            for r in rows:
                for k, v in r.get("_key_accuracies", {}).items():
                    all_key_accs[k].append(v or 0)

            avg_key_accs = {
                k: round(sum(v) / len(v), 1) for k, v in all_key_accs.items()
            }
            agg["_key_accuracies"] = avg_key_accs

            for k, v in avg_key_accs.items():
                agg[f"key_{k}"] = v

            aggregated.append(agg)

        self.data = aggregated

    # ── Grouping ─────────────────────────────────────────────────────

    def _group_by_party(self):
        """Group data by party, creating tree view with indent levels."""
        if not self.data:
            return

        grouped = defaultdict(list)
        for row in self.data:
            party = row.get(Col.PARTY) or _("No Party")
            row["indent"] = 1
            grouped[party].append(row)

        tree_data = []
        for party, rows in grouped.items():
            rows.sort(key=self._sort_key)
            tree_data.append(self._group_row(party, rows))
            tree_data.extend(rows)

        self.data = tree_data

    @staticmethod
    def _sort_key(row):
        """Sort key for child rows: AI Model → PDF Processor."""
        return (
            _AI_MODEL_ORDER.get(row.get(Col.AI_MODEL), 99),
            _PDF_PROCESSOR_ORDER.get(row.get(Col.PDF_PROCESSOR), 99),
        )

    def _group_row(self, party, rows):
        """Aggregated summary row for a party group (indent 0)."""
        count = len(rows)
        row = {
            Col.PARTY: party,
            Col.PARTY_NAME: rows[0].get(Col.PARTY_NAME),
            Col.CURRENCY: rows[0].get(Col.CURRENCY),
            Col.RUN_COUNT: sum(r.get(Col.RUN_COUNT, 1) for r in rows),
            "indent": 0,
        }

        # collect all log names from children
        row[Col.LOG_NAMES] = ",".join(
            r.get(Col.LOG_NAMES) for r in rows if r.get(Col.LOG_NAMES)
        )

        for field in _AVG_FIELDS:
            vals = [r.get(field) or 0 for r in rows]
            row[field] = round(sum(vals) / count, 2) if count else 0

        for field in _SUM_FIELDS:
            row[field] = round(sum(r.get(field) or 0 for r in rows), 6)

        # aggregate per-key accuracies across all child rows
        all_key_accs: dict[str, list[float]] = defaultdict(list)
        for r in rows:
            for k, v in r.get("_key_accuracies", {}).items():
                all_key_accs[k].append(v or 0)

        avg_key_accs = {k: round(sum(v) / len(v), 1) for k, v in all_key_accs.items()}
        for k, v in avg_key_accs.items():
            row[f"key_{k}"] = v

        row["_key_accuracies"] = avg_key_accs

        return row
