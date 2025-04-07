erpnext.TransactionController = class CustomTransactionController extends erpnext.TransactionController {
	async item_code(doc, cdt, cdn) {
		if (!doc.is_created_by_transaction_parser) {
			await super.item_code(doc, cdt, cdn);
			return;
		}

		let row = locals[cdt][cdn];
		const old_values = {
			rate: row.rate,
		};

		await super.item_code(doc, cdt, cdn);

		for (let key in old_values) {
			frappe.model.set_value(cdt, cdn, key, old_values[key]);
		}
	}
};
