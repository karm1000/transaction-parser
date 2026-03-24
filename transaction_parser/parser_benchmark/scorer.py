import frappe
from deepdiff import DeepDiff
from frappe.utils import flt


def _normalize_empty(obj):
    """Recursively convert empty strings to None so `""` vs `None` is not a mismatch.

    Leaves `0`, `False`, and other falsy values untouched.
    """
    if isinstance(obj, dict):
        return {k: _normalize_empty(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_normalize_empty(v) for v in obj]

    if obj == "":
        return None

    return obj


def score_response(expected: dict, actual: dict, max_diffs: int = 500) -> dict:
    """Compare AI response against expected result using DeepDiff."""
    expected = _normalize_empty(expected)
    actual = _normalize_empty(actual)

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

    distance = diff.get("deep_distance", 0)
    accuracy = flt((1 - distance) * 100, 2)

    return {
        "accuracy_score": accuracy,
        "mismatches": _format_mismatches(diff),
    }


_CHANGED_TYPES = {"values_changed", "type_changes"}
_REMOVED_TYPES = {"dictionary_item_removed", "iterable_item_removed"}
_ADDED_TYPES = {"dictionary_item_added", "iterable_item_added"}
_HANDLED_TYPES = _CHANGED_TYPES | _REMOVED_TYPES | _ADDED_TYPES | {"deep_distance"}


def _format_mismatches(diff: DeepDiff) -> list[dict]:
    """Flatten DeepDiff into a simple list of {field, expected, actual}."""
    mismatches = []

    for path, change in diff.get("values_changed", {}).items():
        mismatches.append(
            {
                "field": path,
                "expected": change["old_value"],
                "actual": change["new_value"],
            }
        )

    for path, change in diff.get("type_changes", {}).items():
        mismatches.append(
            {
                "field": path,
                "expected": change["old_value"],
                "actual": change["new_value"],
            }
        )

    for path, val in diff.get("dictionary_item_removed", {}).items():
        mismatches.append({"field": path, "expected": val, "actual": None})

    for path, val in diff.get("dictionary_item_added", {}).items():
        mismatches.append({"field": path, "expected": None, "actual": val})

    for path, val in diff.get("iterable_item_removed", {}).items():
        mismatches.append({"field": path, "expected": val, "actual": None})

    for path, val in diff.get("iterable_item_added", {}).items():
        mismatches.append({"field": path, "expected": None, "actual": val})

    # catch-all for unhandled DeepDiff change types
    for change_type, changes in diff.items():
        if change_type in _HANDLED_TYPES:
            continue

        if isinstance(changes, dict):
            for path, val in changes.items():
                mismatches.append(
                    {"field": f"{change_type}: {path}", "expected": None, "actual": val}
                )
        else:
            mismatches.append(
                {"field": change_type, "expected": None, "actual": str(changes)}
            )

    return mismatches
