import frappe
from frappe import _

BASE_PATH = "transaction_parser.transaction_parser.controllers"
REGIONAL_OVERRIDES_MODULE = "regional_overrides"


def get_controller(country, doctype):
    # TODO: get country & doctype specific controller from hooks (custom implementations)

    if controller := _get_controller(country, doctype):
        return controller

    # TODO: get `other country` & doctype specific controller from hooks (custom implementations)

    if controller := _get_controller("Other", doctype):
        return controller

    if controller := _get_default_controller(doctype):
        return controller

    frappe.throw(_(f"No controller found for {doctype}"))


def _get_controller(country, doctype):
    _country = frappe.scrub(country)
    _class = _get_class_name(country, doctype)

    return _get_attr(f"{BASE_PATH}.{REGIONAL_OVERRIDES_MODULE}.{_country}.{_class}")


def _get_default_controller(doctype):
    return _get_attr(f"{BASE_PATH}.{doctype}.{doctype}")


def _get_class_name(*args):
    return "".join([arg.title().replace(" ", "") for arg in args])


def _get_attr(path):
    try:
        return frappe.get_attr(path)

    except Exception:
        return
