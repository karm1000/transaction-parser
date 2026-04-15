// Copyright (c) 2026, Resilient Tech and contributors
// For license information, please see license.txt

const AI_MODELS = [
	"DeepSeek Chat",
	"DeepSeek Reasoner",
	"OpenAI gpt-4o",
	"OpenAI gpt-4o-mini",
	"OpenAI gpt-5",
	"OpenAI gpt-5-mini",
	"Google Gemini Pro-2.5",
	"Google Gemini Flash-2.5",
];

const PDF_PROCESSORS = ["PDFtoText", "OCRMyPDF", "Docling"];

const PARTY_TYPE_MAP = {
	"Sales Order": "Customer",
	Expense: "Supplier",
};

function make_options(items, txt) {
	return items
		.filter((v) => !txt || v.toLowerCase().includes(txt.toLowerCase()))
		.map((v) => ({ value: v, description: "" }));
}

frappe.query_reports["Transaction Parser Version Comparison"] = {
	tree: true,
	initial_depth: 1,

	onload(report) {
		set_party_type(report);
	},

	formatter(value, row, column, data, default_formatter) {
		if (column.fieldname === "log_names" && value) {
			const names = value.split(",").filter(Boolean);
			if (!names.length) return value;

			const filters = frappe.utils.get_url_from_dict({
				name: JSON.stringify(["in", names]),
			});
			const url = `/app/parser-benchmark-log?${filters}`;
			return `<a href="${url}" target="_blank">See Logs (${names.length})</a>`;
		}
		return default_formatter(value, row, column, data);
	},

	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "transaction_type",
			label: __("Transaction Type"),
			fieldtype: "Select",
			options: "\nSales Order\nExpense",
			reqd: 1,
			default: "Sales Order",
			on_change() {
				set_party_type(frappe.query_report);
			},
		},
		{
			fieldname: "party_type",
			label: __("Party Type"),
			fieldtype: "Link",
			options: "DocType",
			hidden: 1,
		},
		{
			fieldname: "party",
			label: __("Party"),
			fieldtype: "Dynamic Link",
			options: "party_type",
		},
		{
			fieldname: "ai_model",
			label: __("AI Model"),
			fieldtype: "MultiSelectList",
			get_data: (txt) => make_options(AI_MODELS, txt),
		},
		{
			fieldname: "pdf_processor",
			label: __("PDF Processor"),
			fieldtype: "MultiSelectList",
			get_data: (txt) => make_options(PDF_PROCESSORS, txt),
		},
		{
			fieldname: "include_disabled_datasets",
			label: __("Include Disabled Datasets"),
			fieldtype: "Check",
			default: 0,
		},
		{
			fieldname: "is_multiple_files",
			label: __("Multiple Files Only"),
			fieldtype: "Check",
			default: 0,
		},
	],
};

function set_party_type(report) {
	const transaction_type = report.get_filter_value("transaction_type");
	const party_type = PARTY_TYPE_MAP[transaction_type] || "";
	report.set_filter_value("party_type", party_type);
}
