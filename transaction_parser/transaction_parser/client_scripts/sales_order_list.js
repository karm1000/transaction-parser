const DOCTYPE = "Sales Order";
const SUPPORTED_COUNTRIES = ["India", "Other"];
// TODO: remove redundancy
const SUPPORTED_MODELS = ["DeepSeek Chat", "DeepSeek Reasoner", "OpenAI gpt-4o", "OpenAI gpt-4o-mini"];

frappe.listview_settings[DOCTYPE].onload = function (list_view) {
	list_view.page.add_menu_item(__("Parse Purchase Order"), function () {
		let default_country = frappe.defaults.get_default("country") || "Other";

		if (!SUPPORTED_COUNTRIES.includes(default_country)) {
			default_country = "Other";
		}

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
					fieldname: "page_limit",
					label: __("Page Limit"),
					fieldtype: "Int",
				},
				{
					fieldname: "country",
					label: __("Country"),
					fieldtype: "Select",
					options: SUPPORTED_COUNTRIES.join("\n"),
					default: default_country,
					reqd: 1,
				},
				{
					fieldname: "use_default_ai_model",
					label: __("Use Default AI Model"),
					fieldtype: "Check",
					default: 1,
				},
				{
					fieldname: "ai_model",
					label: __("AI Model"),
					fieldtype: "Select",
					options: SUPPORTED_MODELS.join("\n"),
					depends_on: "eval:!doc.use_default_ai_model",
					mandatory_depends_on: "eval:!doc.use_default_ai_model",
				},
			],
			primary_action_label: __("Submit"),
			primary_action(values) {
				frappe.call({
					method: "transaction_parser.transaction_parser.parse",
					args: {
						doctype: DOCTYPE,
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
