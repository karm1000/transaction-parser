# Copyright (c) 2026, Resilient Tech and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ParserBenchmarkTokenCost(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        ai_model: DF.Literal[
            "DeepSeek Chat",
            "DeepSeek Reasoner",
            "OpenAI gpt-4o",
            "OpenAI gpt-4o-mini",
            "OpenAI gpt-5",
            "OpenAI gpt-5-mini",
            "Google Gemini Pro-2.5",
            "Google Gemini Flash-2.5",
        ]
        currency: DF.Link
        input_cost_per_million: DF.Currency
        output_cost_per_million: DF.Float
        parent: DF.Data
        parentfield: DF.Data
        parenttype: DF.Data
    # end: auto-generated types

    pass
