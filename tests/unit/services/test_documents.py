import io
import zipfile

import pytest

from beauty_creator_agent.services.documents import DocumentExtractionError, extract_reference


def test_extracts_plain_text_as_transient_untrusted_reference() -> None:
    reference = extract_reference(
        filename="launch-brief.txt",
        data=b"Write a calm Xiaohongshu post.",
        role="brief",
    )

    assert reference.source_id.startswith("upload:")
    assert reference.role == "brief"
    assert reference.sha256
    assert "<untrusted_document>" in reference.content
    assert "Write a calm Xiaohongshu post." in reference.content


def test_extracts_docx_text_without_persisting_the_file() -> None:
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>Contains ceramides</w:t></w:r></w:p>"
            "</w:body></w:document>",
        )

    reference = extract_reference(
        filename="product.docx", data=payload.getvalue(), role="product_material"
    )

    assert "Contains ceramides" in reference.content
    assert reference.media_type.endswith("document")


def test_rejects_unknown_file_types() -> None:
    with pytest.raises(DocumentExtractionError, match="Only TXT"):
        extract_reference(filename="brief.exe", data=b"not executable", role="brief")


def test_extracts_selectable_pdf_text() -> None:
    pdf = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 43 >>
stream
BT /F1 12 Tf 72 720 Td (PDF product brief) Tj ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000275 00000 n 
0000000345 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
438
%%EOF
"""

    reference = extract_reference(filename="brief.pdf", data=pdf, role="brief")

    assert "PDF product brief" in reference.content
