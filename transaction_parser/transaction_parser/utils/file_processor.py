import io
from tempfile import TemporaryFile

import frappe
import ocrmypdf
from frappe import _
from PyPDF2 import PdfReader, PdfWriter


class FileProcessor:
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
        reader = PdfReader(self.file)
        pages = ""

        for index, page in enumerate(reader.pages):
            # TODO: keep minimum text length ?
            if not page.extract_text():
                pages += f"{index + 1},"

        self.file.seek(0)

        if not pages:
            return

        temp_file = TemporaryFile()
        ocrmypdf.ocr(
            input_file=self.file,
            output_file=temp_file,
            pages=pages,
            progress_bar=False,
            rotate_pages=True,
            force_ocr=True,
            deskew=True,
        )

        self.file = temp_file

    def _get_text(self):
        reader = PdfReader(self.file)

        text = ""
        for page in reader.pages:
            text += page.extract_text()

        return text.replace("\x00", "")
