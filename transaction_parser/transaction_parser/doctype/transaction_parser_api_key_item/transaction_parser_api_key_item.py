# Copyright (c) 2025, Resilient Tech and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class TransactionParserAPIKeyItem(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        api_key: DF.Password
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
        service_provider: DF.Literal["DeepSeek", "OpenAI", "Google", "Anthropic"]
    # end: auto-generated types
    pass
