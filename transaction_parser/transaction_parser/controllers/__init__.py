import frappe
from frappe import _

BASE_PATH = "transaction_parser.transaction_parser.controllers"
REGIONAL_OVERRIDES_MODULE = "regional_overrides"
CUSTOM_OVERRIDES_HOOK = "transaction_parser_overrides"


def get_controller(country, doctype):
    if controller := _get_controller(country, doctype):
        return controller

    if (country != "Other") and (controller := _get_controller("Other", doctype)):
        return controller

    if controller := _get_base_controller(doctype):
        return controller

    frappe.throw(_(f"No controller found for {doctype}"))


def _get_controller(country, doctype):
    if controller := _get_controller_from_hooks(country, doctype):
        return controller

    _module = frappe.scrub(country)
    _class = _get_class_name(country, doctype)

    # TODO: support directory structure also
    return _get_attr(f"{BASE_PATH}.{REGIONAL_OVERRIDES_MODULE}.{_module}.{_class}")


def _get_controller_from_hooks(country, doctype):
    """
    Hook Example:

    transaction_parser_overrides = {
        "India": {
            "Transaction": [
                "path.to.controller.ClassName",
            ],
            "Sales Order": [
                "path.to.controller.ClassName",
            ]
        },
        "Other": {
            "Transaction": [
                "path.to.controller.ClassName",
            ],
            "Sales Order": [
                "path.to.controller.ClassName",
            ]
        },
        "Base": {
            "Transaction": [
                "path.to.controller.ClassName",
            ],
            "Sales Order": [
                "path.to.controller.ClassName",
            ]
        }
    }
    """
    overrides = frappe.get_hooks(CUSTOM_OVERRIDES_HOOK)

    if not overrides:
        return

    if not (country_overrides := overrides.get(country)):
        return

    if not (doctype_overrides := country_overrides.get(doctype)):
        return

    if not (import_path := doctype_overrides[-1]):
        return

    return _get_attr(import_path)


def _get_class_name(*args):
    return "".join([arg.title().replace(" ", "") for arg in args])


def _get_attr(path):
    try:
        return frappe.get_attr(path)

    except Exception:
        return


def _get_base_controller(doctype):
    if found := _get_controller_from_hooks("Base", doctype):
        return found

    _module = frappe.scrub(doctype)
    _class = _get_class_name(doctype)

    return _get_attr(f"{BASE_PATH}.{_module}.{_class}")
