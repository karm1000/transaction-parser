const DOCTYPE = "Purchase Invoice";

frappe.listview_settings[DOCTYPE].onload = async function (list_view) {
	transaction_parser.create_transaction_parser_dialog("Expense", list_view); // eslint-disable-line no-undef
};
