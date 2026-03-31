from dataclasses import dataclass
from typing import Any

from frappe import _dict


@dataclass
class FieldType:
    """Base class for field types in schema."""

    required: bool

    def is_empty(self, value: Any) -> bool:
        """Check if a value is considered empty."""
        return (
            value is None
            or value == ""
            or (isinstance(value, list | dict) and len(value) == 0)
        )


@dataclass
class PrimitiveField(FieldType):
    """Represents a primitive field (string, number, date, etc.)."""

    pass


@dataclass
class ObjectField(FieldType):
    """Represents a nested object field with child fields."""

    children: dict[str, FieldType]


@dataclass
class ListField(FieldType):
    """Represents a list/array field."""

    item_type: FieldType  # Type of items in the list


class SchemaParser:
    """Parses document schema and builds structured field type hierarchy."""

    def parse(self, schema: dict) -> dict[str, FieldType]:
        """
        Parse schema dictionary into structured field types.

        Args:
            schema: Schema dictionary to parse

        Returns:
            Dictionary mapping field names to FieldType instances
        """
        fields = {}

        for key, value in schema.items():
            fields[key] = self._parse_field(value)

        return fields

    def _parse_field(self, schema_value: Any) -> FieldType:
        """
        Parse a single field value into appropriate FieldType.

        Args:
            schema_value: Value from schema (string, list, or dict)

        Returns:
            Appropriate FieldType instance
        """
        # List field: schema value is a list
        if isinstance(schema_value, list):
            required = self._is_required(schema_value)

            # Empty list or primitive list items
            if not schema_value:
                return ListField(
                    required=required, item_type=PrimitiveField(required=True)
                )

            item_schema = schema_value[0]

            # List of objects (e.g., item_list)
            if isinstance(item_schema, dict):
                item_fields = self.parse(item_schema)
                return ListField(
                    required=required,
                    item_type=ObjectField(required=True, children=item_fields),
                )

            # List of primitives (e.g., emails, phones)
            else:
                return ListField(
                    required=required,
                    item_type=PrimitiveField(required=self._is_required(item_schema)),
                )

        # Object field: schema value is a dict
        elif isinstance(schema_value, dict):
            children = self.parse(schema_value)
            return ObjectField(required=True, children=children)

        # Primitive field: schema value is a string
        else:
            return PrimitiveField(required=self._is_required(schema_value))

    def _is_required(self, schema_value: Any) -> bool:
        """
        Check if field is required based on schema notation.

        Args:
            schema_value: Schema value (string or other type)

        Returns:
            True if required, False if optional
        """
        if isinstance(schema_value, str):
            return "| null" not in schema_value and "| 0" not in schema_value

        return True


class ResponseMerger:
    """Schema-driven merger for AI responses from multiple attachments."""

    def __init__(self, response: dict, schema: dict):
        """
        Initialize ResponseMerger with a base response and optional schema.

        Args:
            response: Initial response dict from first file parsing
            schema: Document schema dict for automatic field detection
        """
        self.response = _dict(response) if isinstance(response, dict) else response
        self.schema = schema

        # Parse schema into structured field types
        parser = SchemaParser()
        self.fields = parser.parse(schema)

    def is_complete(self) -> bool:
        """
        Check if all required fields are filled.

        Returns:
            True if complete, False otherwise
        """
        return len(self.get_missing_fields()) == 0

    def get_missing_fields(self) -> list[str]:
        """
        Get list of missing required field paths.

        Returns:
            List of dot-separated field paths that are missing
        """
        missing = []
        self._check_missing_fields(self.fields, self.response, "", missing)
        return missing

    def _check_missing_fields(
        self,
        fields: dict[str, FieldType],
        data: dict,
        path_prefix: str,
        missing: list[str],
    ) -> None:
        """
        Recursively check for missing required fields.

        Args:
            fields: Field type definitions
            data: Current data dict to check
            path_prefix: Current path prefix for nested fields
            missing: List to append missing field paths to
        """
        for key, field_type in fields.items():
            field_path = f"{path_prefix}.{key}" if path_prefix else key
            value = data.get(key) if isinstance(data, dict) else None

            # Check primitive fields
            if isinstance(field_type, PrimitiveField):
                if field_type.required and field_type.is_empty(value):
                    missing.append(field_path)

            # Check object fields recursively
            elif isinstance(field_type, ObjectField):
                if field_type.required and field_type.is_empty(value):
                    missing.append(field_path)

                elif value:
                    self._check_missing_fields(
                        field_type.children, value, field_path, missing
                    )

            # List fields are checked during merging, not at top level
            # (we care about item contents, not just list existence)

    def merge(self, new_response: dict) -> None:
        """
        Merge new response into existing response.

        Args:
            new_response: New response dict to merge from
        """
        self._merge_fields(self.fields, self.response, new_response)

    def _merge_fields(
        self,
        fields: dict[str, FieldType],
        target: dict,
        source: dict,
    ) -> None:
        """
        Merge source data into target based on field definitions.

        Args:
            fields: Field type definitions
            target: Target dict to merge into
            source: Source dict to merge from
        """
        for key, field_type in fields.items():
            source_value = source.get(key)

            # Skip if source doesn't have this field
            if source_value is None:
                continue

            # Handle primitive fields
            if isinstance(field_type, PrimitiveField):
                self._merge_primitive(target, key, source_value)

            # Handle object fields
            elif isinstance(field_type, ObjectField):
                self._merge_object(field_type, target, key, source_value)

            # Handle list fields
            elif isinstance(field_type, ListField):
                self._merge_list(field_type, target, key, source_value)

    def _merge_primitive(self, target: dict, key: str, source_value: Any) -> None:
        """
        Merge primitive field value.

        Args:
            target: Target dict
            key: Field key
            source_value: Value from source
        """
        # Only fill if target is empty
        if not target.get(key) and source_value:
            target[key] = source_value

    def _merge_object(
        self,
        field_type: ObjectField,
        target: dict,
        key: str,
        source_value: dict,
    ) -> None:
        """
        Merge object field recursively.

        Args:
            field_type: ObjectField definition
            target: Target dict
            key: Field key
            source_value: Object value from source
        """
        # Ensure target has the object
        if key not in target:
            target[key] = {}

        # Recursively merge children
        self._merge_fields(field_type.children, target[key], source_value)

    def _merge_list(
        self,
        field_type: ListField,
        target: dict,
        key: str,
        source_value: list,
    ) -> None:
        """
        Merge list field by matching items.

        Args:
            field_type: ListField definition
            target: Target dict
            key: Field key
            source_value: List value from source
        """
        target_list = target.get(key, [])

        # If target list is empty, use source list
        if not target_list:
            target[key] = source_value
            return

        # If source list is empty, nothing to merge
        if not source_value:
            return

        # Only merge if items are objects (not primitive lists)
        if not isinstance(field_type.item_type, ObjectField):
            return

        # Match and merge items
        for target_item in target_list:
            matched_item = self._find_matching_item(
                target_item, source_value, field_type.item_type
            )
            if matched_item:
                self._merge_fields(
                    field_type.item_type.children, target_item, matched_item
                )

    def _find_matching_item(
        self,
        target_item: dict,
        source_items: list[dict],
        item_type: ObjectField,
    ) -> dict | None:
        """
        Find matching item in source list using intelligent matching.

        Matching strategy:
        - Extract key fields from item schema (party_item_code, quantity, rate, description)
        - Require at least 2 matching fields for a match

        Args:
            target_item: Item to find match for
            source_items: List of candidate items
            item_type: ObjectField describing item structure

        Returns:
            Matching item or None
        """
        # Define priority key fields for matching
        key_field_names = ["party_item_code", "quantity", "rate", "description"]

        # Filter to only fields that exist in schema
        available_keys = [
            name for name in key_field_names if name in item_type.children
        ]

        # Try to find match
        for source_item in source_items:
            if self._items_match(target_item, source_item, available_keys):
                return source_item

        return None

    def _items_match(
        self,
        item1: dict,
        item2: dict,
        key_fields: list[str],
    ) -> bool:
        """
        Check if two items match based on key fields.

        Requires at least 2 matching fields.

        Args:
            item1: First item
            item2: Second item
            key_fields: List of key field names to check

        Returns:
            True if items match, False otherwise
        """
        matches = 0

        for field in key_fields:
            value1 = item1.get(field)
            value2 = item2.get(field)

            # Both must exist and be equal
            if value1 and value2 and value1 == value2:
                matches += 1

        # Require at least 2 matching fields
        return matches >= 2
