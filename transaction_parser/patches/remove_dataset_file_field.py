"""
Migrate `file` field data on Parser Benchmark Dataset to Frappe File attachments.

Before the `file` column is dropped (pre_model_sync), ensure every Dataset that
had a file URL stored in the `file` field has a corresponding File doc properly
linked via `attached_to_doctype` / `attached_to_name`.
"""

import frappe


def execute():
    if not frappe.db.has_column("Parser Benchmark Dataset", "file"):
        return

    datasets = frappe.get_all(
        "Parser Benchmark Dataset",
        filters={"file": ("is", "set")},
        fields=["name", "file"],
    )

    for ds in datasets:
        file_url = ds.file
        if not file_url:
            continue

        # Check if a properly-linked File doc already exists
        existing = frappe.db.exists(
            "File",
            {
                "file_url": file_url,
                "attached_to_doctype": "Parser Benchmark Dataset",
                "attached_to_name": ds.name,
            },
        )

        if existing:
            continue

        # Try to find an unlinked File doc with the same URL and link it
        unlinked = frappe.db.get_value(
            "File",
            {"file_url": file_url},
            ["name", "attached_to_doctype", "attached_to_name"],
            as_dict=True,
        )

        if unlinked:
            if not unlinked.attached_to_doctype:
                # Link the orphan File doc to this dataset
                frappe.db.set_value(
                    "File",
                    unlinked.name,
                    {
                        "attached_to_doctype": "Parser Benchmark Dataset",
                        "attached_to_name": ds.name,
                    },
                )
            else:
                # File is attached to something else — create a copy
                _create_attachment(ds.name, file_url)
        else:
            # No File doc exists at all — create one
            _create_attachment(ds.name, file_url)


def _create_attachment(dataset_name: str, file_url: str):
    """Create a new File doc attached to the given dataset."""
    f = frappe.new_doc("File")
    f.file_url = file_url
    f.attached_to_doctype = "Parser Benchmark Dataset"
    f.attached_to_name = dataset_name
    f.insert(ignore_permissions=True)
