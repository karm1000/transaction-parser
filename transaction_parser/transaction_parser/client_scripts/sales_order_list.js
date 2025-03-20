const DOCTYPE = "Sales Order";
const SUPPORTED_COUNTRIES = ["India", "Other"];

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
					fieldname: "file",
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
			],
			primary_action_label: __("Submit"),
			primary_action(values) {
				frappe.call({
					method: "transaction_parser.transaction_parser.parser.parse",
					args: {
						doctype: DOCTYPE,
						country: values.country,
						file_url: values.file,
						page_limit: values.page_limit,
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
