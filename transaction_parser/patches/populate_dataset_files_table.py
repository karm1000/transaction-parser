"""
Populate the new ``files`` child table on Parser Benchmark Dataset.

After model_sync creates the ``Parser Benchmark Dataset File`` child table,
this patch reads the File documents that were previously attached (by the
``remove_dataset_file_field`` pre_model_sync patch) and inserts them as child
rows so the new child-table based workflow works seamlessly.
"""

import frappe


def execute():
    datasets = frappe.get_all("Parser Benchmark Dataset", fields=["name"])

    for ds in datasets:
        # Skip if already has files in child table
        if frappe.db.count("Parser Benchmark Dataset File", {"parent": ds.name}):
            continue

        # Find File docs attached to this dataset
        files = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Parser Benchmark Dataset",
                "attached_to_name": ds.name,
            },
            fields=["file_url", "file_type"],
        )

        if not files:
            continue

        for idx, f in enumerate(files, 1):
            child = frappe.new_doc("Parser Benchmark Dataset File")
            child.update(
                {
                    "parent": ds.name,
                    "parenttype": "Parser Benchmark Dataset",
                    "parentfield": "files",
                    "idx": idx,
                    "file": f.file_url,
                    "file_type": f.file_type or "",
                }
            )
            child.db_insert()

        # Update is_multiple_files flag
        is_multiple = 1 if len(files) > 1 else 0
        frappe.db.set_value(
            "Parser Benchmark Dataset", ds.name, "is_multiple_files", is_multiple
        )
