import frappe
from frappe.utils import cint


def execute():
    """Enqueue recalculation of accuracy scores for all completed Parser Benchmark Logs."""
    log_names = frappe.get_all(
        "Parser Benchmark Log",
        filters={"status": "Completed", "ai_response": ["is", "set"]},
        pluck="name",
    )

    if not log_names:
        return

    frappe.enqueue(
        recalculate_accuracy,
        log_names=log_names,
        queue="long",
        timeout=3600,
    )


def recalculate_accuracy(log_names: list[str]):
    """Recalculate accuracy scores for the given Parser Benchmark Logs.

    Uses cached docs for datasets to avoid repeated DB reads.
    Commits in batches of 100 to avoid long-running transactions.
    """
    from transaction_parser.parser_benchmark.scorer import score_response

    settings = frappe.get_cached_doc("Parser Benchmark Settings")
    weights = {row.key: row.weight for row in (settings.key_weights or [])}
    precision = cint(frappe.db.get_default("float_precision")) or 2

    BATCH_SIZE = 100

    for idx, log_name in enumerate(log_names, start=1):
        try:
            _recalculate_log(log_name, weights, precision, score_response)
        except Exception:
            frappe.log_error(
                title=f"Recalculate Accuracy: {log_name}",
                message=frappe.get_traceback(),
            )

        if idx % BATCH_SIZE == 0:
            frappe.db.commit()  # nosemgrep

    frappe.db.commit()  # nosemgrep


def _recalculate_log(log_name, weights, precision, score_response):
    """Rescore a single log and update its score details."""
    log = frappe.get_doc("Parser Benchmark Log", log_name)

    if not log.ai_response:
        return

    dataset = frappe.get_cached_doc("Parser Benchmark Dataset", log.dataset)

    if not dataset.expected_fields:
        return

    ai_content = frappe.parse_json(log.ai_response)

    result = score_response(
        expected_fields=[
            {"key": row.key, "expected_json": row.expected_json}
            for row in dataset.expected_fields
        ],
        actual=ai_content,
        weights=weights,
        precision=precision,
    )

    # clear old score details
    log.score_details = []

    for detail in result["details"]:
        log.append(
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

    log.accuracy_score = result["overall_accuracy"]
    log.flags.ignore_validate = True
    log.save(ignore_permissions=True)
