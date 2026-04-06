# Copyright (c) 2026, Resilient Tech and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce

PARTY_TYPE_MAP = {
    "Sales Order": "Customer",
    "Expense": "Supplier",
}


def execute(filters=None):
    filters = frappe._dict(filters or {})
    report = BenchmarkLogDetailReport(filters)
    return report.run()


class BenchmarkLogDetailReport:
    def __init__(self, filters: frappe._dict):
        self.filters = filters
        self._set_party_type()

    def run(self):
        logs = self._fetch_logs()
        if not logs:
            return self._get_columns(), []

        log_names = [r.log_name for r in logs]
        score_details_map = self._fetch_score_details(log_names)

        data = [self._build_row(r, score_details_map) for r in logs]

        # discover all unique key names for dynamic columns
        all_keys = dict.fromkeys(
            k for row in data for k in (row.pop("_key_accuracies", None) or {})
        )

        return self._get_columns(list(all_keys)), data

    # ── Columns ──────────────────────────────────────────────────────

    def _get_columns(self, key_names=None):
        columns = [
            {
                "fieldname": "log_name",
                "label": _("Log"),
                "fieldtype": "Link",
                "options": "Parser Benchmark Log",
                "width": 160,
            },
            {
                "fieldname": "dataset",
                "label": _("Dataset"),
                "fieldtype": "Link",
                "options": "Parser Benchmark Dataset",
                "width": 140,
            },
            {
                "fieldname": "party",
                "label": _("Party"),
                "fieldtype": "Data",
                "width": 160,
            },
            {
                "fieldname": "ai_model",
                "label": _("AI Model"),
                "fieldtype": "Data",
                "width": 170,
            },
            {
                "fieldname": "pdf_processor",
                "label": _("Processor"),
                "fieldtype": "Data",
                "width": 100,
            },
            {
                "fieldname": "accuracy_score",
                "label": _("Accuracy (%)"),
                "fieldtype": "Percent",
                "width": 115,
            },
            {
                "fieldname": "status",
                "label": _("Status"),
                "fieldtype": "Data",
                "width": 90,
            },
            {
                "fieldname": "commit_hash",
                "label": _("Commit"),
                "fieldtype": "Data",
                "width": 90,
            },
            {
                "fieldname": "commit_message",
                "label": _("Commit Message"),
                "fieldtype": "Data",
                "width": 200,
            },
            {
                "fieldname": "creation",
                "label": _("Date"),
                "fieldtype": "Datetime",
                "width": 160,
            },
            {
                "fieldname": "total_time",
                "label": _("Total (s)"),
                "fieldtype": "Float",
                "width": 90,
                "precision": 2,
            },
            {
                "fieldname": "total_cost",
                "label": _("Cost"),
                "fieldtype": "Currency",
                "width": 90,
                "options": "currency",
            },
            {
                "fieldname": "total_tokens",
                "label": _("Tokens"),
                "fieldtype": "Int",
                "width": 85,
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

        return columns

    # ── Query ────────────────────────────────────────────────────────

    def _fetch_logs(self):
        log = frappe.qb.DocType("Parser Benchmark Log")
        ds = frappe.qb.DocType("Parser Benchmark Dataset")
        cust = frappe.qb.DocType("Customer")
        supp = frappe.qb.DocType("Supplier")

        statuses = ["Completed"]
        if self.filters.get("include_failed"):
            statuses.append("Failed")

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
                log.creation,
                log.status,
                log.ai_model,
                log.pdf_processor,
                log.accuracy_score,
                log.total_time,
                log.total_cost,
                log.total_tokens,
                log.currency,
                log.dataset,
                log.commit_hash,
                log.commit_message,
                ds.party,
                Coalesce(cust.customer_name, supp.supplier_name, ds.party).as_(
                    "party_name"
                ),
            )
            .where(log.status.isin(statuses))
            .where(ds.docstatus == 1)
            .orderby(log.creation, order=frappe.qb.desc)
        )

        if not self.filters.get("include_disabled_datasets"):
            query = query.where(ds.enabled == 1)

        if self.filters.get("is_multiple_files"):
            query = query.where(ds.is_multiple_files == 1)

        for column, key in (
            (ds.company, "company"),
            (ds.transaction_type, "transaction_type"),
            (ds.party_type, "party_type"),
            (ds.party, "party"),
            (log.dataset, "dataset"),
        ):
            if self.filters.get(key):
                query = query.where(column == self.filters[key])

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
        if not log_names:
            return {}

        sd = frappe.qb.DocType("Parser Benchmark Score Detail")
        rows = (
            frappe.qb.from_(sd)
            .select(sd.parent, sd.key, sd.accuracy)
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
        transaction_type = self.filters.get("transaction_type")
        if transaction_type and not self.filters.get("party_type"):
            self.filters["party_type"] = PARTY_TYPE_MAP.get(transaction_type)

    def _build_row(self, r, score_details_map):
        details = score_details_map.get(r.log_name, [])
        key_accuracies = {d["key"]: d["accuracy"] for d in details}

        commit_msg = (r.commit_message or "").split("\n")[0][:80]

        row = {
            "log_name": r.log_name,
            "dataset": r.dataset,
            "party": r.party_name or r.party or _("No Party"),
            "ai_model": r.ai_model,
            "pdf_processor": r.pdf_processor,
            "accuracy_score": r.accuracy_score if details else "",
            "status": r.status,
            "commit_hash": (r.commit_hash or "")[:7],
            "commit_message": commit_msg,
            "creation": r.creation,
            "total_time": r.total_time,
            "total_cost": r.total_cost,
            "total_tokens": r.total_tokens,
            "currency": r.currency,
            "_key_accuracies": key_accuracies,
        }

        for k, v in key_accuracies.items():
            row[f"key_{k}"] = v

        return row
