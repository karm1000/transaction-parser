import frappe
from frappe.utils import flt


def _normalize(obj):
    """Recursively normalize values for comparison.

    - Empty strings → None
    - Strings → stripped and lowercased
    - frappe._dict → plain dict
    """
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_normalize(v) for v in obj]

    if obj == "":
        return None

    if isinstance(obj, str):
        return obj.strip().lower()

    return obj


def _compare_scalar(
    expected, actual, path: str, precision: int
) -> tuple[int, int, list]:
    """Compare two scalar (non-dict, non-list) values.

    Returns (matched, total, mismatches).
    """
    if expected is None and actual is None:
        return 1, 1, []

    if expected is None or actual is None:
        return 0, 1, [{"field": path, "expected": expected, "actual": actual}]

    # numeric comparison with tolerance
    if isinstance(expected, int | float) and isinstance(actual, int | float):
        if flt(expected, precision) == flt(actual, precision):
            return 1, 1, []
        return 0, 1, [{"field": path, "expected": expected, "actual": actual}]

    # string comparison (already lowered by _normalize)
    if str(expected) == str(actual):
        return 1, 1, []

    return 0, 1, [{"field": path, "expected": expected, "actual": actual}]


def _compare(expected, actual, path: str, precision: int) -> tuple[int, int, list]:
    """Recursively compare expected vs actual, counting leaf field matches.

    Only keys/indices present in `expected` are scored — extra keys in
    `actual` are ignored.  Lists are compared index-by-index (order matters).

    Returns (matched, total, mismatches).
    """
    if isinstance(expected, dict):
        matched = total = 0
        mismatches = []

        for key, exp_val in expected.items():
            child_path = f"{path}.{key}" if path else key
            act_val = actual.get(key) if isinstance(actual, dict) else None
            m, t, mm = _compare(exp_val, act_val, child_path, precision)
            matched += m
            total += t
            mismatches.extend(mm)

        return matched, total, mismatches

    if isinstance(expected, list):
        matched = total = 0
        mismatches = []
        actual_list = actual if isinstance(actual, list) else []

        for idx, exp_item in enumerate(expected):
            child_path = f"{path}[{idx}]"
            act_item = actual_list[idx] if idx < len(actual_list) else None

            if act_item is None:
                # missing actual item — count all leaves in expected as mismatched
                m, t, mm = _compare(exp_item, None, child_path, precision)
                mismatches.extend(mm)
            else:
                m, t, mm = _compare(exp_item, act_item, child_path, precision)
                mismatches.extend(mm)

            matched += m
            total += t

        return matched, total, mismatches

    # scalar
    return _compare_scalar(expected, actual, path, precision)


def score_key(expected, actual, key: str, precision: int = 2) -> dict:
    """Score a single top-level key.

    Args:
        expected: The expected value (parsed JSON) for this key.
        actual: The actual AI response value for this key.
        key: The key name (used as path prefix in mismatch reports).
        precision: Decimal precision for numeric comparisons.

    Returns:
        {"key": str, "matched": int, "total": int, "accuracy": float, "mismatches": list}
    """
    exp_normalized = _normalize(expected)
    act_normalized = _normalize(actual)

    matched, total, mismatches = _compare(
        exp_normalized, act_normalized, key, precision
    )

    accuracy = flt((matched / total) * 100, 2) if total else 100.0

    return {
        "key": key,
        "matched": matched,
        "total": total,
        "accuracy": accuracy,
        "mismatches": mismatches,
    }


def score_response(
    expected_fields: list[dict],
    actual: dict,
    *,
    weights: dict[str, float] | None = None,
    precision: int = 2,
) -> dict:
    """Score AI response against expected fields with per-key breakdown.

    Args:
        expected_fields: List of {"key": str, "expected_json": str|dict} rows
            from the Dataset child table.
        actual: The full AI response dict.
        weights: {key_name: weight} from Settings. Defaults to 1 for all keys.
        precision: Decimal precision for numeric comparisons.

    Returns:
        {"overall_accuracy": float, "details": list[dict]}
        where each detail is the output of score_key().
    """
    weights = weights or {}
    details = []

    weighted_matched = 0.0
    weighted_total = 0.0

    for row in expected_fields:
        key = row["key"]
        expected = row["expected_json"]

        if isinstance(expected, str):
            expected = frappe.parse_json(expected)

        actual_value = actual.get(key) if isinstance(actual, dict) else None
        result = score_key(expected, actual_value, key, precision)
        details.append(result)

        w = weights.get(key, 1.0)
        weighted_matched += result["matched"] * w
        weighted_total += result["total"] * w

    overall_accuracy = (
        flt((weighted_matched / weighted_total) * 100, 2) if weighted_total else 0.0
    )

    return {
        "overall_accuracy": overall_accuracy,
        "details": details,
    }
