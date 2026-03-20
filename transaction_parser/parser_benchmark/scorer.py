import frappe
from deepdiff import DeepDiff, DeepHash
from frappe.utils import flt


def score_response(expected: dict, actual: dict, max_diffs: int = 500) -> dict:
    """Compare AI response against expected result using DeepDiff."""
    diff = DeepDiff(
        expected,
        actual,
        ignore_string_case=True,
        ignore_order=True,
        ignore_type_in_groups=[(dict, frappe._dict)],
        significant_digits=2,
        verbose_level=2,
        max_diffs=max_diffs,
        log_frequency_in_sec=0,
        get_deep_distance=True,
    )

    distance = diff.get("deep_distance", 1) or 1
    accuracy = flt((1 - distance) * 100, 2)

    return {
        "accuracy_score": accuracy,
        "mismatches": _format_mismatches(diff),
    }


def compute_response_hash(ai_response: dict | str) -> str:
    """Deterministic hash of AI response for consistency tracking across runs."""
    if isinstance(ai_response, str):
        ai_response = frappe.parse_json(ai_response)

    return DeepHash(ai_response)[ai_response][:16]


def _format_mismatches(diff: DeepDiff) -> list[dict]:
    """Flatten DeepDiff into a simple list of {field, expected, actual}."""
    mismatches = []

    for path, change in diff.get("values_changed", {}).items():
        mismatches.append({"field": path, "expected": change["old_value"], "actual": change["new_value"]})

    for path, change in diff.get("type_changes", {}).items():
        mismatches.append({"field": path, "expected": change["old_value"], "actual": change["new_value"]})

    for path, val in diff.get("dictionary_item_removed", {}).items():
        mismatches.append({"field": path, "expected": val, "actual": None})

    for path, val in diff.get("dictionary_item_added", {}).items():
        mismatches.append({"field": path, "expected": None, "actual": val})

    for path, val in diff.get("iterable_item_removed", {}).items():
        mismatches.append({"field": path, "expected": val, "actual": None})

    for path, val in diff.get("iterable_item_added", {}).items():
        mismatches.append({"field": path, "expected": None, "actual": val})

    return mismatches


def get_consistency(dataset: str, ai_model: str, pdf_processor: str = "") -> dict:
    """
    Check how consistent a model's response is for a given dataset + processor combo.

    Returns:
        {
            "total_runs": 5,
            "unique_hashes": 2,
            "consistency": 80.0,  # % of runs with the most common hash
            "hashes": {"abc123": 4, "def456": 1},
        }
    """
    Log = frappe.qb.DocType("Parser Benchmark Log")

    logs = (
        frappe.qb.from_(Log)
        .select(Log.response_hash)
        .where(Log.dataset == dataset)
        .where(Log.ai_model == ai_model)
        .where(Log.pdf_processor == (pdf_processor or ""))
        .where(Log.status == "Completed")
        .where(Log.response_hash.isnotnull())
        .run(as_dict=True)
    )

    if not logs:
        return {"total_runs": 0, "unique_hashes": 0, "consistency": 0.0, "hashes": {}}

    # count occurrences of each hash
    hashes = {}
    for log in logs:
        h = log.response_hash
        hashes[h] = hashes.get(h, 0) + 1

    total_runs = len(logs)
    most_common_count = max(hashes.values())
    consistency = flt((most_common_count / total_runs) * 100, 2)

    return {
        "total_runs": total_runs,
        "unique_hashes": len(hashes),
        "consistency": consistency,
        "hashes": hashes,
    }
