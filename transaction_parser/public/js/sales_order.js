frappe.ui.form.on("Sales Order", {
	customer(frm) {
		if (!frm.doc.is_created_by_transaction_parser) {
			return;
		}

		for (const item of frm.doc.items || []) {
			item.__old_rate = item.rate;
		}
	},
});

frappe.ui.form.on("Sales Order Item", {
	rate(frm, cdt, cdn) {
		if (!frm.doc.is_created_by_transaction_parser) {
			return;
		}

		const item = frappe.get_doc(cdt, cdn);

		const old_rate = item.__old_rate;
		item.__old_rate = undefined;

		if (old_rate === undefined || old_rate === item.rate) {
			return;
		}

		frappe.model.set_value(cdt, cdn, "rate", old_rate);
	},
});
