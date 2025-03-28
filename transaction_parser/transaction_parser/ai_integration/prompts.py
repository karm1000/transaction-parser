INPUT_DOCUMENTS = {
    "Sales Order": "Purchase Order",
}


def get_system_prompt(doctype, schema):
    return (
        "You are a JSON data extraction and validation expert for your company's ERP platform.\n"
        "Your role is to analyze the documents and generate a structured JSON output following specific schemas and business rules.\n"
        f"Generate {doctype} for given {INPUT_DOCUMENTS.get(doctype) or 'document'}.\n"
        "When processing documents:\n"
        "1. Extract all relevant data points according to the provided schema\n"
        "2. Format data in the correct types (strings, numbers, dates, etc.)\n"
        "3. Apply region-specific validations (e.g., tax codes, business identifiers)\n"
        "4. Validate and calculate taxes and totals accurately\n"
        "5. Ensure all required fields are present\n"
        "6. Format dates in ISO format (YYYY-MM-DD)\n"
        "7. Use standardized codes for currencies, countries and units\n"
        "8. Validate email addresses and phone numbers and format them correctly as per the region\n"
        "9. Calculate and validate numerical totals\n"
        "10. Include nested objects and arrays as specified\n"
        "11. Handle optional fields appropriately\n"
        "12. Maintain consistent naming conventions\n"
        "13. Validate business identifiers\n"
        "14. Apply appropriate decimal precision for monetary values\n"
        "The output should be valid JSON that can be parsed and processed by automated systems.\n"
        "Json Format:\n\n"
        f"{schema}"
    )


def get_user_prompt(data):
    return (
        f"Extract and validate the following document data into JSON format:\n\n{data}"
    )
