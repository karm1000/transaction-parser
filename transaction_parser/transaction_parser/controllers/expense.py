import frappe
from frappe import _

from transaction_parser.transaction_parser.ai_integration.parser import AIParser
from transaction_parser.transaction_parser.ai_integration.prompts import (
    get_expense_account_system_prompt,
    get_expense_account_user_prompt,
)
from transaction_parser.transaction_parser.controllers.transaction import Transaction


class Expense(Transaction):
    """Expense transaction processor for Purchase Invoices."""

    DOCTYPE = "Purchase Invoice"
    PARTY_DOCTYPE = "Supplier"

    ###################################
    ########## Output Schema ##########
    ###################################

    def get_default_schema(self) -> dict:
        return {
            **super().get_default_schema(),
            "purchase_order_date": "date | null (Also called `Order Date`. It can be different than Document Date)",
            "purchase_order_number": "string | null (Purchase Order number if available)",
            "company": {
                "shipping": self.get_party_schema(),
                "billing": self.get_party_schema(),
            },
            "supplier": self.get_party_schema(),
        }

    ##################################
    ########## Data Mapping ##########
    ##################################

    def set_details(self) -> None:
        self.doc.company = self.get_company()
        if not self.doc.company:
            frappe.throw(_("Company not found"))

        self.doc.supplier = self.get_supplier()

        self.doc.bill_no = self.data.document_number

        if existing_invoice := frappe.db.exists(
            "Purchase Invoice", {"bill_no": self.doc.bill_no, "docstatus": 1}
        ):
            frappe.throw(
                _(
                    "Duplicate Purchase Invoice {existing_invoice} found with Bill number {bill_no}"
                ).format(existing_invoice=existing_invoice, bill_no=self.doc.bill_no)
            )

        self.doc.bill_date = self.data.purchase_order_date
        self.doc.currency = self.data.currency or None

        self.doc.billing_address = self.get_company_billing_address()
        self.doc.shipping_address = self.get_company_shipping_address()
        self.doc.supplier_address = self.get_supplier_address()

        self.doc.contact_person = self.get_contact(
            emails=(
                self.data.company.billing.contact.email
                + self.data.company.shipping.contact.email
            ),
            phones=(
                self.data.company.billing.contact.phone
                + self.data.company.shipping.contact.phone
            ),
        )

        self.doc.items = self.get_items()
        self.set_expense_accounts()
        self.doc.terms = self.get_terms()

    def set_missing_values(self) -> None:
        self.doc.set_missing_values()
        self.doc.calculate_taxes_and_totals()

    def get_company(self) -> str | None:
        self.company_found_against = "company"
        if self.company:
            return self.company

        party_type = "Company"
        fieldname = "name"

        company_identification_order = (
            ("company", self.data.company.billing),
            ("company", self.data.company.shipping),
            ("supplier", self.data.supplier),
        )

        # search
        for key, party in company_identification_order:
            if found := self.search_party(party, party_type, fieldname):
                self.company_found_against = key
                return found

        # guess
        party_names = frappe.get_all(party_type, pluck="name")
        for key, party in company_identification_order:
            if found := self.guess_party(party, party_type, party_names):
                self.company_found_against = key
                return found

    def get_supplier(self) -> str | None:
        self.supplier_found_against = "supplier"
        if self.party:
            return self.party

        party_type = "Supplier"
        fieldname = "supplier_name"

        supplier_identification_order = (
            ("supplier", self.data.supplier),
            ("company", self.data.company.billing),
            ("company", self.data.company.shipping),
        )

        # search
        for key, party in supplier_identification_order:
            if key == self.company_found_against:
                continue

            if found := self.search_party(party, party_type, fieldname):
                self.supplier_found_against = key
                return found

        # guess
        party_names = dict(
            frappe.get_all(party_type, fields=["name", fieldname], as_list=True)
        )
        for key, party in supplier_identification_order:
            if key == self.company_found_against:
                continue

            if found := self.guess_party(party, party_type, party_names):
                self.supplier_found_against = key
                return found

    def get_company_billing_address(self):
        return self._get_company_address("billing")

    def get_company_shipping_address(self):
        return self._get_company_address("shipping")

    def _get_company_address(self, address_type: str):
        address_details = (
            getattr(self.data.company, address_type)
            if self.company_found_against == "company"
            else self.data.supplier
        )

        return self.get_address(
            frappe._dict({**address_details, "name": self.doc.company}),
            "Company",
            address_details,
        )

    def get_supplier_address(self):
        supplier_address_details = (
            (self.data.supplier,)
            if self.supplier_found_against == "supplier"
            else (self.data.company.billing, self.data.company.shipping)
        )

        for detail in supplier_address_details:
            if found := self.get_address(
                frappe._dict({**detail, "name": self.doc.supplier}),
                "Supplier",
                detail,
            ):
                return found

    def get_items(self) -> list:
        if not self.data.item_list:
            return []

        items = []
        mapped_indices = set()

        # Try mapping using Purchase Order if available
        po_number = self.data.purchase_order_number
        if po_number:
            self.map_purchase_order_items(po_number, items, mapped_indices)

        latest_items = self.get_latest_items(self.doc.supplier)

        # For remaining items, try matching with latest items
        for index, item in enumerate(self.data.item_list):
            if index in mapped_indices:
                continue

            choices = {row.item_code: row.description for row in latest_items}
            expense_account_map = {
                row.item_code: row.expense_account for row in latest_items
            }

            if choices:
                matched_item_code = self.guess_value(item.description, choices)
                if matched_item_code:
                    items.append(
                        self.get_item(
                            item,
                            matched_item_code,
                            expense_account=expense_account_map.get(
                                matched_item_code, None
                            ),
                        )
                    )
                    continue

            # If no match, just use description, rate, qty
            items.append(
                self.get_item(
                    item,
                    None,
                    expense_account=None,
                )
            )

        return items

    def map_purchase_order_items(
        self, po_number: str, items: list, mapped_indices: set
    ) -> None:
        """Map items from Purchase Order."""
        if not frappe.db.exists("Purchase Order", po_number):
            return

        po = frappe.get_doc("Purchase Order", po_number)
        if po.company != self.doc.company:
            return

        for index, item in enumerate(self.data.item_list):
            for po_item in po.items:
                if po_item.get("mapped"):
                    continue

                if (
                    abs(item.rate - po_item.rate) < 0.01
                    and abs(item.quantity - po_item.qty) < 0.01
                ):
                    items.append(
                        self.get_item(
                            item,
                            po_item.item_code,
                            expense_account=po_item.expense_account,
                            purchase_order=po.name,
                        )
                    )
                    mapped_indices.add(index)
                    po_item.mapped = True
                    break

    def get_latest_items(self, supplier):
        invoices = frappe.get_all(
            "Purchase Invoice",
            filters={"supplier": supplier, "docstatus": 1},
            limit=self.settings.invoice_lookback_count,
            pluck="name",
        )
        if not invoices:
            return []

        PURCHASE_INVOICE_ITEM = frappe.qb.DocType("Purchase Invoice Item")
        ITEM = frappe.qb.DocType("Item")

        return (
            frappe.qb.from_(PURCHASE_INVOICE_ITEM)
            .join(ITEM)
            .on(PURCHASE_INVOICE_ITEM.item_code == ITEM.name)
            .select(
                PURCHASE_INVOICE_ITEM.item_code,
                PURCHASE_INVOICE_ITEM.description,
                PURCHASE_INVOICE_ITEM.expense_account,
            )
            .where(PURCHASE_INVOICE_ITEM.parent.isin(invoices))
            .where(ITEM.is_stock_item == 0)
            .run(as_dict=True)
        )

    def get_item(self, item, item_code, **kwargs):
        kwargs["supplier"] = self.doc.supplier

        return frappe.get_doc(
            {
                **super().get_item(item, item_code, **kwargs),
                "doctype": "Purchase Invoice Item",
                "parentfield": "items",
            }
        )

    def set_expense_accounts(self):
        """Set expense accounts for items using AI mapping."""
        items = [row for row in self.doc.items if not row.expense_account]
        if not items:
            return

        expense_accounts = dict(
            frappe.get_all(
                "Account",
                filters={
                    "root_type": "Expense",
                    "is_group": 0,
                    "company": self.doc.company,
                },
                fields=["name", "account_name"],
                as_list=True,
            )
        )

        item_descriptions = [row.description for row in items]

        expense_account_mappings = self.get_expense_account_mapping(
            expense_accounts, item_descriptions
        )

        for row in self.doc.items:
            if not row.expense_account:
                row.expense_account = expense_account_mappings.get(row.description)

    def get_expense_account_mapping(self, expense_accounts, item_descriptions):
        item_descriptions = frappe.get_all(
            "Item", filters={"is_stock_item": 0}, pluck="description"
        )
        messages = (
            {
                "role": "system",
                "content": get_expense_account_system_prompt(
                    self.get_expense_account_schema()
                ),
            },
            {
                "role": "user",
                "content": get_expense_account_user_prompt(
                    expense_accounts, item_descriptions
                ),
            },
        )

        ai_parser = AIParser(self.ai_model)
        response_data = ai_parser.get_content(ai_parser.send_message(messages=messages))
        print(response_data)

        return {row.item_description: row.expense_account for row in response_data}
