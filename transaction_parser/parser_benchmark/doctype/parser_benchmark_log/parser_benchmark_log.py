# Copyright (c) 2026, Resilient Tech and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ParserBenchmarkLog(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        accuracy_score: DF.Percent
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
        ai_parse_time: DF.Float
        ai_response: DF.Code | None
        company: DF.Link | None
        completion_tokens: DF.Int
        country: DF.Literal["India", "Other"]
        currency: DF.Link | None
        dataset: DF.Link
        error: DF.Code | None
        field_mismatches: DF.Code | None
        file_content: DF.Code | None
        file_parse_memory: DF.Float
        file_parse_time: DF.Float
        file_type: DF.Data | None
        input_cost: DF.Currency
        input_token_cost: DF.Currency
        naming_series: DF.Literal["PAR-BM-LOG-"]
        output_cost: DF.Currency
        output_token_cost: DF.Currency
        page_limit: DF.Int
        party: DF.DynamicLink | None
        party_type: DF.Link | None
        pdf_processor: DF.Literal["", "OCRMyPDF", "Docling"]
        prompt_tokens: DF.Int
        response_hash: DF.Data | None
        status: DF.Literal["Queued", "Running", "Completed", "Failed"]
        total_cost: DF.Currency
        total_time: DF.Float
        total_tokens: DF.Int
        transaction_type: DF.Literal["Sales Order", "Expense"]
    # end: auto-generated types

    pass
