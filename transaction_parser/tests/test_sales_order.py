"""Tests for Sales Order generation and processing."""

import copy
import json
import re
from unittest.mock import Mock, patch

import frappe
from frappe.core.doctype.file.file import File
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, today

from transaction_parser.transaction_parser.controllers.sales_order import SalesOrder

SAMPLE_DATA = {
    "document_number": "PO-2024-001",
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
        "contact": {
            "email": ["vendor@test.com"],
            "phone": ["+91-9876543212"],
        },
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


class TestSalesOrder(FrappeTestCase):
    """Test cases for Sales Order generation from transaction parser."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.settings = frappe.get_cached_doc("Transaction Parser Settings")
        cls.settings.enabled = 1
        cls.settings.invoice_lookback_count = 5
        cls.settings.save(ignore_permissions=True)
        cls.settings.reload()

        # Create test file mock
        file_mock = Mock(spec=File)
        file_mock.name = "test_po_document.pdf"
        file_mock.file_name = "test_po_document.pdf"
        file_mock.file_type = "PDF"

        cls.files_mock = [file_mock]

        # Sample parsed data structure
        cls.sample_data = json.loads(json.dumps(SAMPLE_DATA), object_hook=frappe._dict)

    def tearDown(self):
        frappe.db.rollback()

    # ----------------------
    # Basic Functionality Tests
    # ----------------------

    def test_sales_order_initialization(self):
        """Test SalesOrder controller initialization."""
        controller = SalesOrder()
        self.assertEqual(controller.DOCTYPE, "Sales Order")
        self.assertEqual(controller.PARTY_DOCTYPE, "Customer")
        self.assertIsNotNone(controller.settings)

    # ----------------------
    # Schema Tests
    # ----------------------
    def test_get_default_schema(self):
        """Test default schema structure for Sales Order."""
        controller = SalesOrder()
        controller.initialize()
        schema = controller.get_default_schema()

        # Check required fields
        self.assertIn("purchase_order_date", schema)
        self.assertIn("delivery_date", schema)
        self.assertIn("project_reference", schema)
        self.assertIn("buyer", schema)
        self.assertIn("vendor", schema)

        # Check buyer structure
        self.assertIn("shipping", schema["buyer"])
        self.assertIn("billing", schema["buyer"])

        # Check inherited fields from base Transaction class
        self.assertIn("document_number", schema)
        self.assertIn("document_date", schema)
        self.assertIn("currency", schema)
        self.assertIn("item_list", schema)
        self.assertIn("totals", schema)

    # ----------------------
    # Data Mapping Tests
    # ----------------------

    @patch.object(SalesOrder, "_parse_file_content")
    def test_set_details_basic_mapping(self, mock_parse):
        """Test basic field mapping in set_details method."""
        mock_parse.return_value = self.sample_data

        controller = SalesOrder(company="_Test Company", party="_Test TP Customer")
        controller.data = self.sample_data
        controller.doc = frappe.get_doc({"doctype": "Sales Order"})

        controller.set_details()
        doc = controller.doc

        # Test basic field mapping
        self.assertEqual(doc.po_no, "PO-2024-001")
        self.assertEqual(doc.po_date, "2024-01-15")
        self.assertEqual(doc.delivery_date, "2024-02-15")
        self.assertEqual(doc.currency, "INR")
        self.assertEqual(doc.company, "_Test Company")
        self.assertEqual(doc.customer, "_Test TP Customer")

    @patch.object(SalesOrder, "_parse_file_content")
    def test_duplicate_po_number_validation(self, mock_parse):
        """Test validation for duplicate PO numbers."""
        mock_parse.return_value = self.sample_data

        # Create existing Sales Order with same PO number
        existing_so = frappe.get_doc(
            {
                "doctype": "Sales Order",
                "po_no": "PO-2024-001",
                "customer": "_Test TP Customer",
                "company": "_Test Company",
                "transaction_date": today(),
                "delivery_date": today(),
            }
        )
        existing_so.append(
            "items",
            {
                "item_code": "_Test Item for Parser",
                "qty": 1,
                "warehouse": "Stores - _TC",
            },
        )
        existing_so.submit()

        controller = SalesOrder(company="_Test Company", party="_Test TP Customer")
        controller.data = self.sample_data
        controller.doc = frappe.get_doc({"doctype": "Sales Order"})

        self.assertRaisesRegex(
            frappe.ValidationError,
            re.compile(r"Duplicate Sales Order .* found with PO number .*"),
            controller.set_details,
        )

    # ----------------------
    # Company Detection Tests
    # ----------------------

    @patch.object(SalesOrder, "_parse_file_content")
    def test_company_detection_from_vendor(self, mock_parse):
        """Test company detection from vendor information."""
        mock_parse.return_value = self.sample_data

        controller = SalesOrder()
        controller.data = self.sample_data

        company = controller.get_company()
        self.assertEqual(company, "_Test Company")
        self.assertEqual(controller.company_found_against, "vendor")

    # ----------------------
    # Customer Detection Tests
    # ----------------------

    @patch.object(SalesOrder, "_parse_file_content")
    def test_customer_detection_from_buyer(self, mock_parse):
        """Test customer detection from buyer information."""
        mock_parse.return_value = self.sample_data

        controller = SalesOrder()
        controller.data = self.sample_data
        controller.company_found_against = "vendor"  # Company found from vendor

        customer = controller.get_customer()
        self.assertEqual(customer, "_Test TP Customer")

    @patch.object(SalesOrder, "_parse_file_content")
    def test_customer_detection_skips_company_source(self, mock_parse):
        """Test customer detection skips the same source as company."""
        mock_parse.return_value = self.sample_data

        controller = SalesOrder()
        controller.data = self.sample_data
        controller.company_found_against = "buyer"  # Company found from buyer

        # Should skip buyer and look elsewhere
        customer = controller.get_customer()
        # This might return None or find from alternative sources
        self.assertIsNone(customer)

    # ----------------------
    # Item Processing Tests
    # ----------------------

    @patch.object(SalesOrder, "_parse_file_content")
    def test_item_processing(self, mock_parse):
        """Test item processing and mapping."""
        mock_parse.return_value = self.sample_data

        controller = SalesOrder(company="_Test Company", party="_Test TP Customer")
        controller.data = self.sample_data
        controller.doc = frappe.get_doc({"doctype": "Sales Order"})
        controller.doc.customer = "_Test TP Customer"

        items = controller.get_items()

        self.assertEqual(len(items), 1)
        item = items[0]

        self.assertEqual(item.idx, 1)
        self.assertEqual(item.customer_item_code, "CUST-ITEM-001")
        self.assertEqual(item.qty, 10)
        self.assertEqual(item.rate, 100)
        self.assertEqual(item.doctype, "Sales Order Item")
        self.assertEqual(item.parentfield, "items")

    # ----------------------
    # Integration Tests
    # ----------------------
    @patch("transaction_parser.transaction_parser.controllers.transaction.AIParser")
    @patch(
        "transaction_parser.transaction_parser.controllers.transaction.FileProcessor"
    )
    def test_full_generation_flow(self, mock_file_processor, mock_ai_parser):
        """Test full Sales Order generation flow."""
        # Mock file processor
        mock_file_processor.return_value.get_content.return_value = "Sample PDF content"

        # Mock AI parser
        mock_ai_parser_instance = Mock()
        mock_ai_parser_instance.parse.return_value = self.sample_data
        mock_ai_parser.return_value = mock_ai_parser_instance

        controller = SalesOrder(company="_Test Company", party="_Test TP Customer")

        # Mock set_missing_values to avoid complex calculations
        doc = controller.generate(self.files_mock)

        self.assertIsNotNone(doc)
        self.assertEqual(doc.doctype, "Sales Order")
        self.assertEqual(doc.po_no, "PO-2024-001")
        self.assertEqual(doc.customer, "_Test TP Customer")
        self.assertEqual(doc.company, "_Test Company")
        self.assertTrue(doc.is_created_by_transaction_parser)

    # ----------------------
    # Error Handling Tests
    # ----------------------

    @patch.object(SalesOrder, "_parse_file_content")
    def test_missing_company_error(self, mock_parse):
        """Test error handling when company cannot be determined."""
        # Create a deep copy to avoid modifying the original sample data
        modified_data = copy.deepcopy(self.sample_data)
        modified_data.vendor.name = "Unknown Company"
        modified_data.buyer.billing.name = "Unknown Customer"
        modified_data.buyer.shipping.name = "Unknown Customer"

        mock_parse.return_value = modified_data

        controller = SalesOrder()
        controller.data = modified_data
        controller.doc = frappe.get_doc({"doctype": "Sales Order"})

        self.assertRaisesRegex(
            frappe.ValidationError, "Company not found", controller.set_details
        )

    # ----------------------
    # Guess/Search Logic Tests
    # ----------------------
    @patch.object(SalesOrder, "_parse_file_content")
    def test_party_guessing_logic(self, mock_parse):
        """Test fuzzy matching logic for party detection."""
        mock_parse.return_value = self.sample_data

        controller = SalesOrder()
        controller.data = self.sample_data
        result = controller.guess_party(
            self.sample_data.vendor,
            "Company",
            ["_Test Company", "Another Company"],
        )
        self.assertEqual(result, "_Test Company")

    # ----------------------
    # Custom Schema Tests
    # ----------------------
    @change_settings(
        "Transaction Parser Settings",
        {"base_schema": '{"custom_field": "string"}'},
    )
    def test_custom_schema_integration(self):
        """Test integration with custom schema fields."""
        controller = SalesOrder()
        controller.initialize()

        schema = controller.get_schema()
        self.assertTrue("custom_field" in schema)
