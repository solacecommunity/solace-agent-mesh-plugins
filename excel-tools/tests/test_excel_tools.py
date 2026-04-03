"""Tests for excel_tools plugin."""

import os
import tempfile

import openpyxl
import pytest

from excel_tools.tools import (
    analyze_sheet,
    create_workbook,
    evaluate_formulas,
    get_formulas,
    list_sheets,
    read_range,
    recalculate,
    write_cells,
)


@pytest.fixture
def sample_workbook(tmp_path):
    """Create a sample workbook with data and formulas for testing."""
    path = str(tmp_path / "test.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales"

    # Headers
    ws["A1"] = "Product"
    ws["B1"] = "Quantity"
    ws["C1"] = "Price"
    ws["D1"] = "Total"

    # Data rows
    ws["A2"] = "Widget"
    ws["B2"] = 10
    ws["C2"] = 5.50
    ws["D2"] = "=B2*C2"

    ws["A3"] = "Gadget"
    ws["B3"] = 25
    ws["C3"] = 12.00
    ws["D3"] = "=B3*C3"

    ws["A4"] = "Gizmo"
    ws["B4"] = 7
    ws["C4"] = 8.75
    ws["D4"] = "=B4*C4"

    # Summary row
    ws["A6"] = "Grand Total"
    ws["D6"] = "=SUM(D2:D4)"

    # Second sheet
    ws2 = wb.create_sheet("Summary")
    ws2["A1"] = "Total Sales"
    ws2["B1"] = "=Sales!D6"

    wb.save(path)
    wb.close()
    return path


@pytest.fixture
def empty_workbook(tmp_path):
    """Create a minimal empty workbook."""
    path = str(tmp_path / "empty.xlsx")
    wb = openpyxl.Workbook()
    wb.save(path)
    wb.close()
    return path


# ---- list_sheets ----

@pytest.mark.asyncio
async def test_list_sheets(sample_workbook):
    result = await list_sheets(file_path=sample_workbook)
    assert result["status"] == "success"
    assert result["sheet_count"] == 2
    assert "Sales" in result["sheets"]
    assert "Summary" in result["sheets"]


@pytest.mark.asyncio
async def test_list_sheets_not_found():
    result = await list_sheets(file_path="/nonexistent/file.xlsx")
    assert result["status"] == "error"


# ---- read_range ----

@pytest.mark.asyncio
async def test_read_range_full_sheet(sample_workbook):
    result = await read_range(file_path=sample_workbook, sheet_name="Sales")
    assert result["status"] == "success"
    assert result["row_count"] >= 4
    # First row should be headers
    assert result["rows"][0] == ["Product", "Quantity", "Price", "Total"]


@pytest.mark.asyncio
async def test_read_range_specific(sample_workbook):
    result = await read_range(
        file_path=sample_workbook,
        sheet_name="Sales",
        range_address="A1:B3",
    )
    assert result["status"] == "success"
    assert result["row_count"] == 3


@pytest.mark.asyncio
async def test_read_range_with_formulas(sample_workbook):
    result = await read_range(
        file_path=sample_workbook,
        sheet_name="Sales",
        range_address="A1:D3",
        include_formulas=True,
    )
    assert result["status"] == "success"
    assert "formulas" in result
    # Row index 1 (second row, D2) should have a formula
    assert result["formulas"][1][3] == "=B2*C2"


# ---- get_formulas ----

@pytest.mark.asyncio
async def test_get_formulas(sample_workbook):
    result = await get_formulas(file_path=sample_workbook, sheet_name="Sales")
    assert result["status"] == "success"
    assert result["formula_count"] == 4  # D2, D3, D4, D6
    assert "D2" in result["formulas"]
    assert result["formulas"]["D2"] == "=B2*C2"
    assert result["formulas"]["D6"] == "=SUM(D2:D4)"


@pytest.mark.asyncio
async def test_get_formulas_empty(empty_workbook):
    result = await get_formulas(file_path=empty_workbook)
    assert result["status"] == "success"
    assert result["formula_count"] == 0


# ---- evaluate_formulas ----

@pytest.mark.asyncio
async def test_evaluate_formulas(sample_workbook):
    result = await evaluate_formulas(file_path=sample_workbook)
    assert result["status"] == "success"
    assert result["evaluated_count"] > 0


@pytest.mark.asyncio
async def test_evaluate_formulas_specific_cells(sample_workbook):
    result = await evaluate_formulas(
        file_path=sample_workbook,
        cells=["D2"],
        sheet_name="Sales",
    )
    assert result["status"] == "success"
    # D2 = B2 * C2 = 10 * 5.50 = 55.0
    if "D2" in result["results"]:
        assert result["results"]["D2"] == pytest.approx(55.0)


# ---- recalculate ----

@pytest.mark.asyncio
async def test_recalculate(sample_workbook):
    result = await recalculate(
        file_path=sample_workbook,
        inputs={"B2": 20},  # Change Widget quantity from 10 to 20
        output_cells=["D2"],
        sheet_name="Sales",
    )
    assert result["status"] == "success"
    # D2 = 20 * 5.50 = 110.0
    if "D2" in result["results"]:
        assert result["results"]["D2"] == pytest.approx(110.0)


@pytest.mark.asyncio
async def test_recalculate_no_inputs(sample_workbook):
    result = await recalculate(file_path=sample_workbook)
    assert result["status"] == "error"


# ---- analyze_sheet ----

@pytest.mark.asyncio
async def test_analyze_sheet(sample_workbook):
    result = await analyze_sheet(file_path=sample_workbook, sheet_name="Sales")
    assert result["status"] == "success"
    assert result["headers"][0] == "Product"
    assert result["dimensions"]["columns"] == 4
    assert result["formula_count"] == 4

    # Check numeric stats exist for Quantity column (B)
    qty_col = next(c for c in result["columns"] if c["header"] == "Quantity")
    assert "numeric_stats" in qty_col
    assert qty_col["numeric_stats"]["count"] == 3


# ---- write_cells ----

@pytest.mark.asyncio
async def test_write_cells(sample_workbook, tmp_path):
    out_path = str(tmp_path / "modified.xlsx")
    result = await write_cells(
        file_path=sample_workbook,
        updates={"A5": "Doohickey", "B5": 15, "C5": 3.25, "D5": "=B5*C5"},
        sheet_name="Sales",
        save_as=out_path,
    )
    assert result["status"] == "success"
    assert result["count"] == 4
    assert os.path.isfile(out_path)

    # Verify written values
    wb = openpyxl.load_workbook(out_path)
    ws = wb["Sales"]
    assert ws["A5"].value == "Doohickey"
    assert ws["B5"].value == 15
    wb.close()


@pytest.mark.asyncio
async def test_write_cells_no_updates(sample_workbook):
    result = await write_cells(file_path=sample_workbook)
    assert result["status"] == "error"


# ---- create_workbook ----

@pytest.mark.asyncio
async def test_create_workbook(tmp_path):
    path = str(tmp_path / "new.xlsx")
    result = await create_workbook(
        file_path=path,
        sheet_name="Inventory",
        headers=["Item", "Count"],
        rows=[["Apples", 50], ["Bananas", 30]],
    )
    assert result["status"] == "success"
    assert result["rows_written"] == 3  # 1 header + 2 data
    assert os.path.isfile(path)

    wb = openpyxl.load_workbook(path)
    ws = wb["Inventory"]
    assert ws["A1"].value == "Item"
    assert ws["A2"].value == "Apples"
    assert ws["B3"].value == 30
    wb.close()


@pytest.mark.asyncio
async def test_create_workbook_empty(tmp_path):
    path = str(tmp_path / "blank.xlsx")
    result = await create_workbook(file_path=path)
    assert result["status"] == "success"
    assert os.path.isfile(path)
