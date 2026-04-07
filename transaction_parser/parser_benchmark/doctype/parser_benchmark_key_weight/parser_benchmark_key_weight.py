# Copyright (c) 2026, Resilient Tech and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ParserBenchmarkKeyWeight(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        key: DF.Literal[
            "document_number",
            "document_date",
            "currency",
            "item_list",
            "totals",
            "payment_terms",
            "local_terms",
            "delivery_date",
            "buyer",
            "vendor",
            "company",
            "supplier",
        ]
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
        weight: DF.Float
    # end: auto-generated types

    pass
