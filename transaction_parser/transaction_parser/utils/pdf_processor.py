import io
from abc import ABC, abstractmethod

import frappe
import ocrmypdf
import pymupdf
from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter
from frappe import _
from frappe.core.doctype.file.file import File


class BasePDFProcessor(ABC):
    """
    Abstract base class for PDF processors.

    To add a new processor:
    1. Create a new file in pdf_processors/
    2. Subclass BasePDFProcessor
    3. Implement the `process` method
    4. Register it in pdf_processors/__init__.py PDF_PROCESSORS dict
    """

    @abstractmethod
    def process(self, file: io.BytesIO | File, page_limit: int | None = None) -> str:
        """
        Process a PDF file and return extracted text.

        Args:
                file: PDF file as BytesIO stream or Frappe File document
                page_limit: Maximum number of pages to process (None = all pages)

        Returns:
                Extracted text content from the PDF
        """
        ...

    def get_sanitized_file(
        self, file: io.BytesIO | File, page_limit: int | None = None
    ) -> io.BytesIO:
        """Get file as BytesIO stream and trim pages if needed."""
        if isinstance(file, File):
            file = io.BytesIO(file.get_content())

        return self.trim_pages(file, page_limit)

    def trim_pages(self, file: io.BytesIO, page_limit: int | None = None) -> io.BytesIO:
        if not page_limit or page_limit <= 0:
            return file

        input_pdf = pymupdf.open(stream=file, filetype="pdf")

        if input_pdf.page_count <= page_limit:
            input_pdf.close()
            return file

        output_pdf = pymupdf.open()
        output_pdf.insert_pdf(input_pdf, to_page=page_limit - 1)

        temp_file = io.BytesIO()
        output_pdf.save(temp_file)

        output_pdf.close()
        input_pdf.close()

        temp_file.seek(0)
        return temp_file


class DoclingPDFProcessor(BasePDFProcessor):
    """
    PDF processor using Docling for document conversion and text extraction.

    Docling provides advanced document understanding including table detection,
    formula recognition, reading order detection, and OCR.
    """

    def process(self, file: io.BytesIO | File, page_limit: int | None = None) -> str:
        file = self.get_sanitized_file(file, page_limit)

        source = DocumentStream(name="document.pdf", stream=file)
        converter = DocumentConverter()
        result = converter.convert(source)

        return result.document.export_to_markdown()


class OCRPDFProcessor(BasePDFProcessor):
    """
    PDF processor using PyMuPDF for text extraction and OCRmyPDF for OCR.
    """

    def process(self, file: io.BytesIO | File, page_limit: int | None = None) -> str:
        file = self.get_sanitized_file(file, page_limit)
        file = self.apply_ocr(file)

        return self.get_text(file)

    def apply_ocr(self, file: io.BytesIO) -> io.BytesIO:
        doc = pymupdf.open(stream=file, filetype="pdf")
        pages_to_ocr = [
            str(i) for i, page in enumerate(doc, 1) if not page.get_text("text").strip()
        ]

        doc.close()

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


# Registry: add new processors here
PDF_PROCESSORS: dict[str, type[BasePDFProcessor]] = {
    "OCR": OCRPDFProcessor,
    "Docling": DoclingPDFProcessor,
}

DEFAULT_PDF_PROCESSOR = "OCR"


def get_pdf_processor(name: str | None = None) -> BasePDFProcessor:
    """
    Factory function to get a PDF processor by name.

    Usage:

    ```
    processor = get_pdf_processor("OCR")
    text = processor.process(file, page_limit=5)
    ```
    """
    name = name or DEFAULT_PDF_PROCESSOR

    processor_class = PDF_PROCESSORS.get(name)
    if not processor_class:
        supported = ", ".join(PDF_PROCESSORS.keys())
        frappe.throw(
            title=_("Unsupported PDF Processor"),
            msg=_("PDF Processor '{0}' is not supported. <br>Choose from: {1}").format(
                name, supported
            ),
        )

    return processor_class()
