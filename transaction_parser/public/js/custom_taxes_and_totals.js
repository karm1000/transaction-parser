const { prototype } = erpnext.taxes_and_totals;
const apply_pricing_rule_on_item = prototype.apply_pricing_rule_on_item;

prototype.apply_pricing_rule_on_item = function (item) {
	if (this.frm.doc.is_created_by_transaction_parser) {
		return;
	}

	return apply_pricing_rule_on_item.call(this, arguments);
};
