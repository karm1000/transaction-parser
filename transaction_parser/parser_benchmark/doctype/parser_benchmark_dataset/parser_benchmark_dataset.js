// Copyright (c) 2026, Resilient Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on("Parser Benchmark Dataset", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.enabled) {
			frm.add_custom_button(__("Run Benchmark"), () => run_benchmark(frm));
		}
	},

	transaction_type(frm) {
		set_party_type(frm);
	},
});

function run_benchmark(frm) {
	frappe.call({
		method: "transaction_parser.parser_benchmark.doctype.parser_benchmark_dataset.parser_benchmark_dataset.run_benchmark",
		args: { dataset_name: frm.doc.name },
		freeze: true,
		freeze_message: __("Queuing benchmarks..."),
		callback(r) {
			if (r.message && r.message.length) {
				frappe.show_alert({
					message: __("{0} benchmark(s) queued.", [r.message.length]),
					indicator: "green",
				});
				frappe.set_route("List", "Parser Benchmark Log", {
					dataset: frm.doc.name,
					status: "Queued",
				});
			} else {
				frappe.show_alert({
					message: __("No benchmarks queued. Check model/processor selections."),
					indicator: "red",
				});
			}
		},
	});
}

const PARTY_TYPE_MAP = {
	"Sales Order": "Customer",
	Expense: "Supplier",
};

function set_party_type(frm) {
	const party_type = PARTY_TYPE_MAP[frm.doc.transaction_type];
	if (party_type && frm.doc.party_type !== party_type) {
		frm.set_value("party_type", party_type);
	}
}
