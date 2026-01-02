frappe.ui.form.on("Sales Order", {
	setup(frm) {
		if (!frm.doc.is_created_by_transaction_parser) {
			return;
		}

		frm.cscript.customer = function () {
			erpnext.utils.get_party_details(this.frm, null, null);
		};
	},
});
