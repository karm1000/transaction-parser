const SUPPORTED_COUNTRIES = ["India", "Other"];

const TRANSACTION_LABEL_MAP = {
	"Sales Order": __("Sales Order"),
	Expense: __("Expense Invoice"),
};

async function create_transaction_parser_dialog(transaction_type, list_view) {
	const { default_model, supported_models } = await get_available_ai_models();

	list_view.page.add_menu_item(__("Parse " + TRANSACTION_LABEL_MAP[transaction_type]), function () {
		const transaction_dialog = new frappe.ui.Dialog({
			title: __("Upload " + TRANSACTION_LABEL_MAP[transaction_type]),
			fields: [
				{
					fieldname: "file_url",
					label: __("File"),
					fieldtype: "Attach",
					reqd: 1,
					description: __("Supported formats: PDF, CSV, Excel (XLSX, XLS)"),
					onchange: function () {
						toggle_page_limit_field(transaction_dialog);
					},
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "page_limit",
					label: __("Page Limit"),
					fieldtype: "Int",
					description: __("Only applicable for PDF files"),
				},
				{
					fieldtype: "Section Break",
				},
				{
					fieldname: "ai_model",
					label: __("AI Model"),
					fieldtype: "Select",
					options: supported_models,
					default: default_model,
					reqd: 1,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "country",
					label: __("Country"),
					fieldtype: "Select",
					options: SUPPORTED_COUNTRIES.join("\n"),
					default: get_default_country(),
					reqd: 1,
				},
			],
			primary_action_label: __("Submit"),
			primary_action(values) {
				frappe.call({
					method: "transaction_parser.transaction_parser.parse",
					args: {
						transaction: transaction_type,
						...values,
					},
					callback: function () {
						frappe.msgprint({
							message: __("Parsing " + TRANSACTION_LABEL_MAP[transaction_type]),
							alert: true,
						});
						transaction_dialog.hide();
					},
				});
			},
		});

		transaction_dialog.show();
	});
}

frappe.provide("transaction_parser");

// eslint-disable-next-line no-undef
Object.assign(transaction_parser, {
	create_transaction_parser_dialog,
});

async function get_available_ai_models() {
	const res = await frappe.call({
		method: "transaction_parser.transaction_parser.doctype.transaction_parser_settings.transaction_parser_settings.get_ai_models",
	});
	return res.message;
}

function get_default_country() {
	const user_country = frappe.defaults.get_default("Country");
	return SUPPORTED_COUNTRIES.includes(user_country) ? user_country : "Other";
}

function toggle_page_limit_field(dialog) {
	const file_url = dialog.get_value("file_url");
	if (!file_url) return;

	// Extract file extension
	const file_extension = file_url.split(".").pop().toLowerCase();
	const is_pdf = file_extension === "pdf";

	// Show/hide page limit field based on file type
	const page_limit_field = dialog.get_field("page_limit");
	if (page_limit_field) {
		if (is_pdf) {
			page_limit_field.df.hidden = 0;
			page_limit_field.refresh();
		} else {
			page_limit_field.df.hidden = 1;
			page_limit_field.refresh();
			// Clear the value for non-PDF files
			dialog.set_value("page_limit", "");
		}
	}
}
