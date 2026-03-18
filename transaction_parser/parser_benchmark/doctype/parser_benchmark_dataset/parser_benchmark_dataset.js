// Copyright (c) 2026, Resilient Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on("Parser Benchmark Dataset", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.enabled) {
			frm.add_custom_button(__("Run Benchmark"), () => run_benchmark(frm));
		}

		set_pdf_processor_options(frm);
	},
});

function run_benchmark(frm) {
	frappe.call({
		method: "transaction_parser.parser_benchmark.doctype.parser_benchmark_dataset.parser_benchmark_dataset.run_benchmark",
		args: { dataset_name: frm.doc.name },
		freeze: true,
		freeze_message: __("Queuing benchmark..."),
		callback(r) {
			if (r.message) {
				frappe.show_alert({
					message: __("Benchmark queued. Redirecting to log..."),
					indicator: "green",
				});
				frappe.set_route("Form", "Parser Benchmark Log", r.message);
			} else {
				frappe.show_alert({
					message: __("Failed to queue benchmark. Please try again."),
					indicator: "red",
				});
			}
		},
	});
}

function set_pdf_processor_options(frm) {
	frappe.call({
		method: "transaction_parser.parser_benchmark.doctype.parser_benchmark_dataset.parser_benchmark_dataset.get_pdf_processors",
		callback(r) {
			if (r.message) {
				frm.set_df_property("pdf_processor", "options", r.message);
			}
		},
	});
}
