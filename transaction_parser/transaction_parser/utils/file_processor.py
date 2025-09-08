import io

import frappe
import ocrmypdf
import pandas as pd
import pymupdf
from frappe import _


class FileProcessor:
    """Process files: PDF (trim pages, apply OCR), CSV/Excel (parse data), extract content."""

    def get_content(self, doc, page_limit=None):
        if doc.file_type == "PDF":
            return self._process_pdf(doc, page_limit)
        elif doc.file_type in ["CSV", "XLSX", "XLS"]:
            return self._process_spreadsheet(doc)
        else:
            frappe.throw(_("Only PDF, CSV, and Excel files are supported"))

    def _process_pdf(self, doc, page_limit=None):
        """Process PDF files with OCR and page limiting."""
        self.file = io.BytesIO(doc.get_content())
        self._remove_extra_pages(page_limit)
        self._apply_ocr()
        return self._get_text()

    def _process_spreadsheet(self, doc):
        """Process CSV and Excel files."""

        if doc.file_type == "CSV":
            file_content_str = self._decode_csv_content(doc.get_content())
            file_content = io.StringIO(file_content_str)
            df = self._read_csv_flexible(file_content)
        elif doc.file_type in ["XLSX", "XLS"]:
            # For Excel files, use BytesIO directly
            file_content = io.BytesIO(doc.get_content())
            df = pd.read_excel(file_content)

        # Convert dataframe to a formatted string representation
        return self._format_dataframe_as_text(df)

    def _read_csv_flexible(self, file_content):
        """Read CSV with flexible parsing to handle different formats."""
        # Reset the StringIO position
        file_content.seek(0)

        try:
            # First try standard CSV reading
            return pd.read_csv(file_content)
        except pd.errors.ParserError:
            # If standard parsing fails, try reading as key-value pairs
            file_content.seek(0)
            return self._read_csv_as_key_value(file_content)

    def _read_csv_as_key_value(self, file_content):
        """Read CSV as key-value pairs (common for forms/documents)."""
        try:
            # Read with only 2 columns max, treating everything after first comma as value
            df = pd.read_csv(
                file_content,
                header=None,
                names=["Key", "Value"],
                sep=",",
                quoting=1,  # QUOTE_ALL
                engine="python",  # More flexible parser
            )
            return df
        except Exception:
            # Last resort: read line by line and split on first comma only
            file_content.seek(0)
            lines = file_content.read().strip().split("\n")
            data = []

            for line in lines:
                if "," in line:
                    # Split only on the first comma
                    key, value = line.split(",", 1)
                    data.append([key.strip(), value.strip()])
                else:
                    # Handle lines without commas
                    data.append([line.strip(), ""])

            return pd.DataFrame(data, columns=["Key", "Value"])

    def _decode_csv_content(self, content_bytes):
        """Decode CSV file content with fallback encodings."""
        encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]

        for encoding in encodings:
            try:
                return content_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue

        # If all encodings fail, try with error handling
        try:
            return content_bytes.decode("utf-8", errors="replace")
        except Exception:
            frappe.throw(
                _(
                    "Unable to decode CSV file. Please ensure the file is saved with a supported encoding."
                )
            )

    def _format_dataframe_as_text(self, df):
        """Convert DataFrame to a text format suitable for AI processing."""
        if df.empty:
            return "No data found in the file."

        # Create a structured text representation
        text_parts = []

        # Check if this looks like key-value pairs
        if (
            len(df.columns) == 2
            and df.columns[0] in ["Key", 0]
            and df.columns[1] in ["Value", 1]
        ):
            # Format as key-value pairs
            text_parts.append("Document Information (Key-Value pairs):")
            text_parts.append("")
            for _, row in df.iterrows():
                key = str(row.iloc[0]).strip()
                value = str(row.iloc[1]).strip()
                if key and value:  # Skip empty entries
                    text_parts.append(f"{key}: {value}")
        else:
            # Format as regular table
            # Add column headers
            headers = " | ".join(df.columns.astype(str))
            text_parts.append(f"Columns: {headers}")
            text_parts.append("")

            # Add data rows
            text_parts.append("Data:")
            for index, row in df.iterrows():
                row_data = " | ".join(row.astype(str))
                text_parts.append(f"Row {index + 1}: {row_data}")

        # Add summary information
        text_parts.append("")
        text_parts.append(f"Total rows: {len(df)}")
        text_parts.append(f"Total columns: {len(df.columns)}")

        return "\n".join(text_parts)

    def _remove_extra_pages(self, page_limit=None):
        if not page_limit:
            return

        input_pdf = pymupdf.open(stream=self.file, filetype="pdf")
        output_pdf = pymupdf.open()
        output_pdf.insert_pdf(input_pdf, to_page=page_limit - 1)

        temp_file = io.BytesIO()
        output_pdf.save(temp_file)

        output_pdf.close()
        input_pdf.close()

        self.file = temp_file
        self.file.seek(0)

    def _apply_ocr(self):
        doc = pymupdf.open(stream=self.file, filetype="pdf")
        pages_to_ocr = [
            str(i) for i, page in enumerate(doc, 1) if not page.get_text("text").strip()
        ]

        if not pages_to_ocr:
            return

        pages = ",".join(pages_to_ocr)

        temp_file = io.BytesIO()
        self.file.seek(0)

        ocrmypdf.ocr(
            input_file=self.file,
            output_file=temp_file,
            pages=pages,
            progress_bar=False,
            rotate_pages=True,
            force_ocr=True,
        )

        self.file = temp_file
        self.file.seek(0)

    def _get_text(self):
        text = ""
        doc = pymupdf.open(stream=self.file, filetype="pdf")
        for page in doc:
            text += page.get_text("text")

        doc.close()

        return text
