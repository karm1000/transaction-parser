import io

import frappe
import ocrmypdf
import pymupdf
from frappe import _


class FileProcessor:
    """Process PDF file: trim pages, apply OCR if needed, extract text."""

    def get_content(self, doc, page_limit=None):
        if doc.file_type != "PDF":
            frappe.throw(_("Only PDF files are supported"))

        self.file = io.BytesIO(doc.get_content())
        self._remove_extra_pages(page_limit)
        self._apply_ocr()

        return self._get_text()

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
