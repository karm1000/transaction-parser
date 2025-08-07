"""Prompt templates for AI document parsing."""

# Mapping of output document types to their corresponding input document types
INPUT_DOCUMENTS = {"Sales Order": "Purchase Order", "Purchase Invoice": "Sales Invoice"}


def get_system_prompt(document_schema: dict) -> str:
    """Generate system prompt for document parsing.

    Args:
        document_schema: JSON schema for the expected output

    Returns:
        Formatted system prompt string
    """
    return f"""You are a JSON data extraction and validation expert for your company's ERP platform.
You will be provided with text data extracted from a document and a JSON schema for the output.

Your role is to:
1. Deeply analyze the given document data
2. Understand the meaning of each field in the document and its relevance to the given document type
3. Think step-by-step and map each field in the document with the given JSON schema
4. Generate a structured JSON output according to the given JSON schema

When processing the document, you will:
1. Extract all relevant data points according to the provided schema
2. Format data in the correct types (strings, numbers, dates, etc.)
3. Apply region-specific validations (e.g., tax codes, business identifiers)
4. Validate and calculate taxes and totals, and other charges accurately
5. Ensure all required fields are present
6. Format dates in ISO format (YYYY-MM-DD)
7. Use standardized codes for currencies, countries and units
8. Validate email addresses and phone numbers and format them correctly as per the region
9. Calculate and validate numerical totals
10. Include nested objects and arrays as specified
11. Handle optional fields appropriately
12. Maintain consistent naming conventions
13. Validate business identifiers
14. Apply appropriate decimal precision for monetary values

JSON schema is given below:
{document_schema}"""


def get_user_prompt(document_type: str, document_data: str) -> str:
    """Generate user prompt for document parsing.

    Args:
        document_type: Type of document to generate
        document_data: Raw document content

    Returns:
        Formatted user prompt string
    """
    input_doc_type = INPUT_DOCUMENTS.get(document_type, "document")

    return f"""Generate {document_type} for given {input_doc_type} according to above JSON schema.
Document data is given below:
{document_data}"""


def get_expense_account_system_prompt(schema: dict) -> str:
    """Generate system prompt for expense account mapping.

    Args:
        schema: JSON schema for expense account mapping output

    Returns:
        Formatted system prompt string
    """
    return f"""You are an intelligent ERP accounting assistant.

Your task is to assign the most appropriate expense account to every item description provided from the provided data. Choose the best match for each item from the provided Expense Accounts list, based on the nature, usage, or purpose of the item.

The output must strictly be a **JSON array**, not wrapped in any object. Do not use keys like 'mappings', 'expense_account_mappings', or anything else.
Always return the output as a JSON **array (list)**, even if there is only one item.

JSON schema for the output is given below:
{schema}"""


def get_expense_account_user_prompt(
    expense_accounts: list, item_descriptions: list
) -> str:
    """Generate user prompt for expense account mapping.

    Args:
        expense_accounts: List of available expense accounts
        item_descriptions: List of item descriptions to map

    Returns:
        Formatted user prompt string
    """
    return f"""Map the following item descriptions to the most appropriate expense accounts from the list provided.
Ensure that each item description is matched with the most relevant expense account based on its nature, usage, or purpose.

Expense Accounts:
{expense_accounts}

Item Descriptions:
{item_descriptions}

Return only the mapping, no explanation."""
