"""
Unit tests for all format-specific chunkers.

Runs without real S3, Qdrant, or OpenAI credentials.
Uses sample in-memory data for each format.
"""
import io
import csv
import pytest
from unittest.mock import patch

from chunkers import route_and_chunk
from chunkers.markdown_chunker import chunk_markdown
from chunkers.pdf_chunker import chunk_pdf
from chunkers.tabular_chunker import chunk_csv, chunk_excel
from utils import Chunk


# ── Fixtures ──────────────────────────────────────────────────────

SAMPLE_MD = b"""# Leave Policy

This document describes the leave policy for all staff.

## Sick Leave

Employees are entitled to 10 days of sick leave per year.
Sick leave must be supported by a medical certificate for absences longer than 3 days.

### How to Apply

1. Log in to the HR portal at https://hr.example.com
2. Navigate to Leave Management
3. Select "Sick Leave" and enter the dates
4. Submit and await approval from your manager

## Annual Leave

Employees are entitled to 20 days of annual leave per year.
Leave must be approved at least 2 weeks in advance.
"""

SAMPLE_CSV_CONTENT = """EmployeeID,Name,Department,LeaveBalance,Manager
E001,Alice Smith,HR,18,Jane Doe
E002,Bob Jones,Finance,12,John Lee
E003,Carol Wu,Engineering,20,Priya Nair
"""


def make_sample_pdf_bytes() -> bytes:
    """Create a minimal but real PDF in memory using reportlab-free approach."""
    # Minimal hand-crafted PDF — no external lib needed for the test
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj

2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj

3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj

4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 72 720 Td (Onboarding Guide) Tj ET
endstream
endobj

5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj

xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000266 00000 n 
0000000360 00000 n 

trailer
<< /Size 6 /Root 1 0 R >>
startxref
441
%%EOF"""
    return pdf_content


def make_sample_excel_bytes() -> bytes:
    """Create a minimal Excel file using openpyxl."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Employees"
    ws.append(["EmployeeID", "Name", "Department", "Role"])
    ws.append(["E001", "Alice Smith", "HR", "HR-Admin"])
    ws.append(["E002", "Bob Jones", "Finance", "Finance"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


# ── Markdown tests ─────────────────────────────────────────────────

class TestMarkdownChunker:
    def test_produces_chunks(self):
        chunks = chunk_markdown(SAMPLE_MD, "staff/leave_policy.md", "General-Staff")
        assert len(chunks) > 0

    def test_all_chunks_are_chunk_instances(self):
        chunks = chunk_markdown(SAMPLE_MD, "staff/leave_policy.md", "General-Staff")
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_access_role_propagated(self):
        chunks = chunk_markdown(SAMPLE_MD, "staff/leave_policy.md", "General-Staff")
        for c in chunks:
            assert c.metadata.access_role == "General-Staff"

    def test_source_propagated(self):
        key = "staff/leave_policy.md"
        chunks = chunk_markdown(SAMPLE_MD, key, "General-Staff")
        for c in chunks:
            assert c.metadata.source == key

    def test_doc_type_is_md(self):
        chunks = chunk_markdown(SAMPLE_MD, "staff/leave_policy.md", "General-Staff")
        for c in chunks:
            assert c.metadata.doc_type == "md"

    def test_no_empty_chunks(self):
        chunks = chunk_markdown(SAMPLE_MD, "staff/leave_policy.md", "General-Staff")
        for c in chunks:
            assert c.text.strip() != ""

    def test_section_metadata_present(self):
        chunks = chunk_markdown(SAMPLE_MD, "staff/leave_policy.md", "General-Staff")
        # At least some chunks should have section metadata
        with_section = [c for c in chunks if c.metadata.section]
        assert len(with_section) > 0


# ── CSV tests ──────────────────────────────────────────────────────

class TestCSVChunker:
    def test_one_chunk_per_row(self):
        raw = SAMPLE_CSV_CONTENT.encode()
        chunks = chunk_csv(raw, "hr/employees.csv", "HR-Admin")
        assert len(chunks) == 3  # 3 data rows

    def test_chunk_contains_column_values(self):
        raw = SAMPLE_CSV_CONTENT.encode()
        chunks = chunk_csv(raw, "hr/employees.csv", "HR-Admin")
        assert "Alice Smith" in chunks[0].text
        assert "HR" in chunks[0].text

    def test_chunk_uses_pipe_delimiter(self):
        raw = SAMPLE_CSV_CONTENT.encode()
        chunks = chunk_csv(raw, "hr/employees.csv", "HR-Admin")
        assert " | " in chunks[0].text

    def test_access_role_set(self):
        raw = SAMPLE_CSV_CONTENT.encode()
        chunks = chunk_csv(raw, "hr/employees.csv", "HR-Admin")
        for c in chunks:
            assert c.metadata.access_role == "HR-Admin"

    def test_doc_type_is_csv(self):
        raw = SAMPLE_CSV_CONTENT.encode()
        chunks = chunk_csv(raw, "hr/employees.csv", "HR-Admin")
        for c in chunks:
            assert c.metadata.doc_type == "csv"

    def test_row_index_stored(self):
        raw = SAMPLE_CSV_CONTENT.encode()
        chunks = chunk_csv(raw, "hr/employees.csv", "HR-Admin")
        indices = [c.metadata.row_index for c in chunks]
        assert indices == sorted(indices)


# ── Excel tests ────────────────────────────────────────────────────

class TestExcelChunker:
    def test_produces_chunks(self):
        raw = make_sample_excel_bytes()
        chunks = chunk_excel(raw, "hr/employees.xlsx", "HR-Admin")
        assert len(chunks) == 2  # 2 data rows

    def test_sheet_name_in_text(self):
        raw = make_sample_excel_bytes()
        chunks = chunk_excel(raw, "hr/employees.xlsx", "HR-Admin")
        assert all("Sheet: Employees" in c.text for c in chunks)

    def test_doc_type_is_xlsx(self):
        raw = make_sample_excel_bytes()
        chunks = chunk_excel(raw, "hr/employees.xlsx", "HR-Admin")
        for c in chunks:
            assert c.metadata.doc_type == "xlsx"


# ── Router tests ───────────────────────────────────────────────────

class TestFormatRouter:
    def test_routes_md(self):
        chunks = route_and_chunk("staff/guide.md", SAMPLE_MD, "General-Staff")
        assert all(c.metadata.doc_type == "md" for c in chunks)

    def test_routes_csv(self):
        raw = SAMPLE_CSV_CONTENT.encode()
        chunks = route_and_chunk("hr/data.csv", raw, "HR-Admin")
        assert all(c.metadata.doc_type == "csv" for c in chunks)

    def test_unsupported_extension_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            route_and_chunk("docs/file.pptx", b"data", "Public")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
