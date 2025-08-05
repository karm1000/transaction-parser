const DOCTYPE = "Purchase Invoice";
frappe.require("assets/transaction_parser/js/transaction_parser_dialog.js");

frappe.listview_settings[DOCTYPE].onload = async function (list_view) {
	create_transaction_parser_dialog("Expense", list_view); // eslint-disable-line no-undef
};
