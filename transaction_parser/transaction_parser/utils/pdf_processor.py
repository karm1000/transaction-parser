import io
from abc import ABC, abstractmethod

import frappe
import pymupdf
from frappe import _
from frappe.core.doctype.file.file import File

DEFAULT_PDF_PROCESSOR = "OCRMyPDF"


class PDFProcessor(ABC):
    """
    Abstract base class for PDF processors.

    To add a new processor from another app:

    1. Subclass PDFProcessor
    2. Implement the `process` method
    3. Register it via the `pdf_processors` hook in your app's hooks.py:

    ```
    pdf_processors = {
        "MyProcessor": "my_app.utils.pdf_processor.MyPDFProcessor",
    }
    ```
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
        pass

    def get_sanitized_file(
        self, file: io.BytesIO | File, page_limit: int | None = None
    ) -> io.BytesIO:
        """
        Get file as BytesIO stream and trim pages if needed.
        """
        if isinstance(file, File):
            file = io.BytesIO(file.get_content())

        return self.trim_pages(file, page_limit)

    def trim_pages(self, file: io.BytesIO, page_limit: int | None = None) -> io.BytesIO:
        if not page_limit or page_limit <= 0:
            file.seek(0)
            return file

        input_pdf = pymupdf.open(stream=file, filetype="pdf")

        if input_pdf.page_count <= page_limit:
            input_pdf.close()
            file.seek(0)
            return file

        output_pdf = pymupdf.open()
        output_pdf.insert_pdf(input_pdf, to_page=page_limit - 1)

        temp_file = io.BytesIO()
        output_pdf.save(temp_file)

        output_pdf.close()
        input_pdf.close()

        temp_file.seek(0)
        return temp_file

    def get_text(self, file: io.BytesIO) -> str:
        text = ""
        doc = pymupdf.open(stream=file, filetype="pdf")

        for page in doc:
            text += page.get_text("text")

        doc.close()

        return text


class DoclingPDFProcessor(PDFProcessor):
    """
    PDF processor using Docling for document conversion and text extraction.

    Docling provides advanced document understanding including table detection,
    formula recognition, reading order detection, and OCR.
    """

    _converter = None

    def process(self, file: io.BytesIO | File, page_limit: int | None = None) -> str:
        from docling.datamodel.base_models import ConversionStatus, DocumentStream

        file = self.get_sanitized_file(file, page_limit)

        source = DocumentStream(name="document.pdf", stream=file)  # temporary name
        converter = self._get_converter()
        result = converter.convert(source)

        if (
            not result
            or not result.document
            or result.status
            not in (
                ConversionStatus.SUCCESS,
                ConversionStatus.PARTIAL_SUCCESS,
            )
        ):
            frappe.throw(
                title=_("PDF Reading Failed"),
                msg=_("Docling failed to read the document."),
            )

        return result.document.export_to_markdown()

    def _get_converter(self):
        if DoclingPDFProcessor._converter is None:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import DocumentConverter, PdfFormatOption

            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = False  # TODO: OCR Setup

            DoclingPDFProcessor._converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
                }
            )

        return DoclingPDFProcessor._converter


class OCRMyPDFProcessor(PDFProcessor):
    """
    PDF processor using PyMuPDF for text extraction and OCRMyPDF for OCR.
    """

    def process(self, file: io.BytesIO | File, page_limit: int | None = None) -> str:
        file = self.get_sanitized_file(file, page_limit)
        file = self.apply_ocr(file)

        return self.get_text(file)

    def apply_ocr(self, file: io.BytesIO) -> io.BytesIO:
        import ocrmypdf

        doc = pymupdf.open(stream=file, filetype="pdf")
        pages_to_ocr = [
            str(i) for i, page in enumerate(doc, 1) if not page.get_text("text").strip()
        ]

        doc.close()
        file.seek(0)

        if not pages_to_ocr:
            return file

        pages = ",".join(pages_to_ocr)

        temp_file = io.BytesIO()

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


def get_pdf_processor(name: str | None = None) -> PDFProcessor:
    """
    Factory function to get a PDF processor by name.

    Usage:

    ```
    processor = get_pdf_processor("Docling")
    text = processor.process(file, page_limit=5)
    ```

    To register a custom processor from another app, add to its hooks.py:

    ```
    pdf_processors = {
        "MyProcessor": "my_app.utils.pdf_processor.MyPDFProcessor",
    }
    ```
    """
    if not name:
        name = (
            frappe.db.get_single_value("Transaction Parser Settings", "pdf_processor")
            or DEFAULT_PDF_PROCESSOR
        )

    processors = frappe.get_hooks("pdf_processors") or {}

    # [-1] → last in resolution order app's overrides will take precedence
    class_path = (processors.get(name) or [None])[-1]

    if not class_path:
        frappe.throw(
            title=_("Unsupported PDF Processor"),
            msg=_("PDF Processor '{0}' is not supported. <br>Choose from: {1}").format(
                name, ", ".join(processors.keys())
            ),
        )

    return frappe.get_attr(class_path)()


def get_available_pdf_processors() -> list[str]:
    """Return names of all registered PDF processors from hooks."""
    processors = frappe.get_hooks("pdf_processors") or {}
    return list(processors.keys())
