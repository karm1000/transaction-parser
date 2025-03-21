import frappe

BASE_PATH = "transaction_parser.transaction_parser.regional_overrides"
VALID_CLASS_TYPES = ("Generator", "Schema")
MODULES = {
    "Generator": "document_generators",
    "Schema": "output_schema_providers",
}


def get_class(country, doctype, class_type):
    if class_type not in VALID_CLASS_TYPES:
        raise ValueError(f"Invalid class type {class_type}")

    return frappe.get_attr(_get_class_path(country, doctype, class_type))


def _get_class_path(country, doctype, class_type):
    _country = frappe.scrub(country)
    _doctype = frappe.scrub(doctype)
    _class = _get_class_name(country, doctype, class_type)
    _module = MODULES.get(class_type)

    return f"{BASE_PATH}.{_country}.{_module}.{_doctype}.{_class}"


def _get_class_name(country, doctype, class_type):
    def _parse(value):
        return value.title().replace(" ", "")

    _country = _parse(country)
    _doctype = _parse(doctype)

    return f"{_country}{_doctype}{class_type}"
