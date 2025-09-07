"""Utility functions and fixtures for transaction parser tests."""

import frappe


def create_test_file_mock(filename="test_document.pdf", content="Sample PDF content"):
    """Create a mock file object for testing."""
    from unittest.mock import Mock

    file_mock = Mock()
    file_mock.name = filename
    file_mock.file_name = filename
    file_mock.file_type = "PDF"
    file_mock.get_content.return_value = content.encode()
    return file_mock


def create_test_sales_order_data():
    """Create sample sales order data for testing."""
    return frappe._dict(
        {
            "document_number": "PO-TEST-001",
            "document_date": "2024-01-15",
            "purchase_order_date": "2024-01-15",
            "delivery_date": "2024-02-15",
            "currency": "INR",
            "buyer": {
                "billing": {
                    "name": "_Test TP Customer",
                    "address": {
                        "address_line_1": "123 Test Street",
                        "address_line_2": "Test Area",
                        "city": "Mumbai",
                        "state": "Maharashtra",
                        "postal_code": "400001",
                        "country": "IN",
                    },
                    "contact": {
                        "email": ["customer@test.com"],
                        "phone": ["+91-9876543210"],
                    },
                },
                "shipping": {
                    "name": "_Test TP Customer",
                    "address": {
                        "address_line_1": "456 Shipping Street",
                        "address_line_2": "Shipping Area",
                        "city": "Mumbai",
                        "state": "Maharashtra",
                        "postal_code": "400002",
                        "country": "IN",
                    },
                    "contact": {
                        "email": ["shipping@test.com"],
                        "phone": ["+91-9876543211"],
                    },
                },
            },
            "vendor": {
                "name": "_Test Company",
                "address": {
                    "address_line_1": "789 Vendor Street",
                    "address_line_2": "Vendor Area",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "postal_code": "400003",
                    "country": "IN",
                },
                "contact": {"email": ["vendor@test.com"], "phone": ["+91-9876543212"]},
            },
            "item_list": [
                {
                    "serial_number": "1",
                    "party_item_code": "CUST-ITEM-001",
                    "description": "_Test Sample Item",
                    "quantity": 10,
                    "unit": "Nos",
                    "rate": 100,
                    "amount": 1000,
                    "discount": 0,
                    "taxes": [],
                    "total_tax_percentage": 18,
                    "total_tax_amount": 180,
                    "is_price_inclusive_of_taxes": False,
                    "delivery_date": "2024-02-15",
                }
            ],
            "totals": {
                "subtotal": 1000,
                "taxes": [{"description": "IGST", "percentage": 18, "amount": 180}],
                "total_tax_percentage": 18,
                "total_tax_amount": 180,
                "grand_total": 1180,
            },
            "payment_terms": [
                {
                    "credit_days": 30,
                    "credit_from": "Invoice Date",
                    "due_date": "2024-02-15",
                    "invoice_portion": 100,
                }
            ],
            "local_terms": {
                "incoterms": "EXW",
                "description": "Standard terms and conditions",
            },
        }
    )


def create_test_company(company_name="_Test Company"):
    """Create or get test company."""
    if not frappe.db.exists("Company", company_name):
        company = frappe.get_doc(
            {
                "doctype": "Company",
                "company_name": company_name,
                "abbr": "_TC",
                "country": "India",
                "default_currency": "INR",
            }
        )
        company.insert(ignore_permissions=True)
    return company_name


def create_test_customer(customer_name="_Test TP Customer"):
    """Create or get test customer."""
    if not frappe.db.exists("Customer", customer_name):
        customer = frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": customer_name,
                "customer_type": "Company",
            }
        )
        customer.insert(ignore_permissions=True)
    return customer_name


def create_test_item(item_code="_Test Sample Item"):
    """Create or get test item."""
    if not frappe.db.exists("Item", item_code):
        item = frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_code,
                "description": item_code,
                "item_group": "All Item Groups",
                "stock_uom": "Nos",
                "is_stock_item": 1,
            }
        )
        item.insert(ignore_permissions=True)
    return item_code


def setup_test_data():
    """Set up all required test data."""
    create_test_company()
    create_test_customer()
    create_test_item()


def cleanup_test_sales_orders():
    """Clean up test sales orders."""
    frappe.db.sql("DELETE FROM `tabSales Order` WHERE po_no LIKE 'PO-TEST-%'")
    frappe.db.commit()


class TransactionParserTestMixin:
    """Mixin class providing common test utilities for transaction parser tests."""

    def setUp_transaction_parser(self):
        """Set up transaction parser test environment."""
        self.settings = frappe.get_cached_doc("Transaction Parser Settings")
        self.settings.enabled = 1
        self.settings.save(ignore_permissions=True)
        setup_test_data()

    def tearDown_transaction_parser(self):
        """Clean up transaction parser test environment."""
        cleanup_test_sales_orders()
        frappe.db.rollback()

    def create_mock_file(self, filename="test_document.pdf"):
        """Create a mock file for testing."""
        return create_test_file_mock(filename)

    def get_sample_data(self):
        """Get sample sales order data."""
        return create_test_sales_order_data()
