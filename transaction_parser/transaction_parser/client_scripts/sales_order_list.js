const DOCTYPE = "Sales Order";
const SUPPORTED_COUNTRIES = ["India", "Other"];

frappe.listview_settings[DOCTYPE].onload = async function (list_view) {
	const { default_model, supported_models } = await get_ai_models();

	list_view.page.add_menu_item(__("Parse Purchase Order"), function () {
		const dialog = new frappe.ui.Dialog({
			title: __("Upload Purchase Order"),
			fields: [
				{
					fieldname: "file_url",
					label: __("File"),
					fieldtype: "Attach",
					reqd: 1,
				},
				{
					fieldtype: "Column Break",
				},
				{
					fieldname: "page_limit",
					label: __("Page Limit"),
					fieldtype: "Int",
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
						transaction: DOCTYPE,
						...values,
					},
					callback: function () {
						frappe.msgprint({
							message: __("Parsing Purchase Order"),
							alert: true,
						});
						dialog.hide();
					},
				});
			},
		});

		dialog.show();
	});
};

async function get_ai_models() {
	// returns an object with two attributes: 1. default_ai_model, 2. supported_ai_models
	const res = await frappe.call({
		method: "transaction_parser.transaction_parser.doctype.transaction_parser_settings.transaction_parser_settings.get_ai_models",
	});
	return res.message;
}

function get_default_country() {
	const country = frappe.defaults.get_default("Country");
	return SUPPORTED_COUNTRIES.includes(country) ? country : "Other";
}
