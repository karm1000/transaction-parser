# Copyright (c) 2026, Resilient Tech and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ParserBenchmarkLog(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        ai_model: DF.Data | None
        ai_parse_time: DF.Float
        ai_response: DF.JSON | None
        completion_tokens: DF.Int
        currency: DF.Link | None
        dataset: DF.Link
        document_name: DF.DynamicLink | None
        document_type: DF.Link | None
        error: DF.Code | None
        file_content: DF.Code | None
        file_parse_memory: DF.Float
        file_parse_time: DF.Float
        input_cost: DF.Currency
        input_token_cost: DF.Currency
        naming_series: DF.Literal["PAR-BM-LOG-"]
        output_cost: DF.Currency
        output_token_cost: DF.Currency
        pdf_processor: DF.Data | None
        prompt_tokens: DF.Int
        status: DF.Literal["Queued", "Running", "Completed", "Failed"]
        total_cost: DF.Currency
        total_time: DF.Float
        total_tokens: DF.Int
    # end: auto-generated types

    pass
