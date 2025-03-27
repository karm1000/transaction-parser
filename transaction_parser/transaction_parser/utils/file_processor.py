import io
from tempfile import TemporaryFile

import frappe
import ocrmypdf
from frappe import _
from PyPDF2 import PdfReader, PdfWriter


class FileProcessor:
    def get_details(self, file_url, page_limit=None):
        doc = frappe.get_last_doc("File", filters={"file_url": file_url})

        if doc.file_type != "PDF":
            frappe.throw(_("Only PDF files are supported"))

        self.file = io.BytesIO(doc.get_content())
        self._remove_extra_pages(page_limit)
        self._apply_ocr()

        text = self._get_text()

        return frappe._dict(
            {
                "filename": doc.file_name,
                "docname": doc.name,
                "content": text,
            }
        )

    def _remove_extra_pages(self, page_limit=None):
        if not page_limit:
            return

        reader = PdfReader(self.file)
        writer = PdfWriter()

        for index, page in enumerate(reader.pages):
            if index >= page_limit:
                break

            writer.add_page(page)

        temp_file = TemporaryFile()
        writer.write(temp_file)
        temp_file.seek(0)

        self.file = temp_file

    def _apply_ocr(self):
        temp_file = TemporaryFile()

        ocrmypdf.ocr(
            input_file=self.file,
            output_file=temp_file,
            force_ocr=True,  # TODO: study its impact
            deskew=True,  # TODO: study its impact
        )

        self.file = temp_file

    def _get_text(self):
        reader = PdfReader(self.file)

        text = ""
        for page in reader.pages:
            text += page.extract_text()

        return text
