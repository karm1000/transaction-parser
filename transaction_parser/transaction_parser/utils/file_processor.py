import io

import frappe
import ocrmypdf
import pymupdf
from frappe import _
from frappe.core.doctype.file.file import File
from frappe.utils.csvutils import read_csv_content
from frappe.utils.xlsxutils import (
    read_xls_file_from_attached_file,
    read_xlsx_file_from_attached_file,
)

# TODO: Make some method static
# TODO: Remove self.file logic
# TODO: Add DI like can use OCR or Docling for PDF processing


class FileProcessor:
    """
    Process files: PDF (trim pages, apply OCR), CSV/Excel (parse data), extract content.
    """

    def get_content(self, doc: File, page_limit: int | None = None) -> str | None:
        if doc.file_type == "PDF":
            return self.process_pdf(doc, page_limit)

        if doc.file_type in ("CSV", "XLSX", "XLS"):
            return self.process_spreadsheet(doc)

        frappe.throw(
            title=_("Unsupported File Type"),
            msg=_("Only PDF, CSV, and Excel files are supported"),
        )

    def process_pdf(self, doc: File, page_limit: int | None = None) -> str:
        """
        Process PDF files with OCR and page limiting.
        """
        file = io.BytesIO(doc.get_content())
        file = self.trim_pages(file, page_limit)
        file = self.apply_ocr(file)

        return self.get_text(file)

    def process_spreadsheet(self, doc: File) -> str:
        """
        Process CSV and Excel files.
        """
        file_content = doc.get_content()

        if doc.file_type == "CSV":
            file_content_str = self.decode_csv_content(file_content)
            rows = read_csv_content(file_content_str)
        elif doc.file_type == "XLSX":
            rows = read_xlsx_file_from_attached_file(fcontent=file_content)
        elif doc.file_type == "XLS":
            rows = read_xls_file_from_attached_file(file_content)

        # Convert rows to a formatted string representation
        return self.format_rows_as_text(rows)

    def decode_csv_content(self, content: str | bytes) -> str:
        """
        Decode CSV file content with fallback encodings.
        """
        # If content is already a string, return as-is
        if isinstance(content, str):
            return content

        # If content is bytes, decode it
        encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]

        for encoding in encodings:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue

        # If all encodings fail, try with error handling
        try:
            return content.decode("utf-8", errors="replace")
        except Exception:
            frappe.throw(
                _(
                    "Unable to decode CSV file. Please ensure the file is saved with a supported encoding."
                )
            )

    def format_rows_as_text(self, rows: list) -> str:
        """
        Convert rows to a text format suitable for AI processing.
        """
        if not rows:
            frappe.throw(_("No data found in the file."))

        # Create a structured text representation
        text_parts = []

        # Check if this looks like key-value pairs (2 columns)
        if len(rows) > 0 and len(rows[0]) == 2:
            # Format as key-value pairs
            text_parts.append("Document Information (Key-Value pairs):")
            text_parts.append("")
            for row in rows:
                key = str(row[0] or "").strip()
                value = str(row[1] or "").strip()
                if key and value:
                    text_parts.append(f"{key}: {value}")
        else:
            # Format as regular table
            # First row is typically headers
            headers = " | ".join(str(cell or "") for cell in rows[0])
            text_parts.append(f"Columns: {headers}")
            text_parts.append("")

            # Add data rows (skip header row)
            text_parts.append("Data:")
            for index, row in enumerate(rows[1:], 1):
                row_data = " | ".join(str(cell or "") for cell in row)
                text_parts.append(f"Row {index}: {row_data}")

        # Add summary information
        text_parts.append("")
        text_parts.append(f"Total rows: {len(rows)}")
        text_parts.append(f"Total columns: {len(rows[0])}")

        return "\n".join(text_parts)

    def trim_pages(self, file: io.BytesIO, page_limit: int | None = None) -> io.BytesIO:
        if not page_limit or page_limit <= 0:
            return file

        input_pdf = pymupdf.open(stream=file, filetype="pdf")
        output_pdf = pymupdf.open()
        output_pdf.insert_pdf(input_pdf, to_page=page_limit - 1)

        temp_file = io.BytesIO()
        output_pdf.save(temp_file)

        output_pdf.close()
        input_pdf.close()

        temp_file.seek(0)
        return temp_file

    def apply_ocr(self, file: io.BytesIO) -> io.BytesIO:
        doc = pymupdf.open(stream=file, filetype="pdf")
        pages_to_ocr = [
            str(i) for i, page in enumerate(doc, 1) if not page.get_text("text").strip()
        ]

        if not pages_to_ocr:
            return file

        pages = ",".join(pages_to_ocr)

        temp_file = io.BytesIO()
        file.seek(0)

        ocrmypdf.ocr(
            input_file=file,
            output_file=temp_file,
            pages=pages,
            progress_bar=False,
            rotate_pages=True,
            force_ocr=True,
        )

        temp_file.seek(0)
        return temp_file

    def get_text(self, file: io.BytesIO) -> str:
        text = ""
        doc = pymupdf.open(stream=file, filetype="pdf")
        for page in doc:
            text += page.get_text("text")

        doc.close()

        return text
