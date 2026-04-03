"""Excel Tools for Solace Agent Mesh.

Provides async tool functions for reading, writing, analyzing, and
reproducing calculations in Excel (.xlsx / .xls) spreadsheets.

Dependencies:
    openpyxl  — read/write .xlsx files, inspect formulas
    formulas  — evaluate Excel formulas in pure Python
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional

import formulas
import openpyxl
from openpyxl.utils import get_column_letter

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _open_workbook(
    file_path: str,
    data_only: bool = False,
) -> openpyxl.Workbook:
    """Open an Excel workbook, raising a clear error on failure."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    return openpyxl.load_workbook(file_path, data_only=data_only)


def _cell_ref(row: int, col: int) -> str:
    """Return an Excel-style cell reference like 'A1'."""
    return f"{get_column_letter(col)}{row}"


def _serialize_cell(cell) -> Any:
    """Convert a cell value to a JSON-safe type."""
    if cell.value is None:
        return None
    if isinstance(cell.value, datetime):
        return cell.value.isoformat()
    return cell.value


def _sheet_names(wb: openpyxl.Workbook) -> List[str]:
    return wb.sheetnames


def _unwrap_value(value: Any) -> Any:
    """Extract a plain Python value from a formulas library result.

    The *formulas* library may return ``Ranges`` objects, numpy arrays,
    or native scalars.  This helper normalises all of them to JSON-safe
    Python types.
    """
    # Ranges object → extract the underlying value array, then unwrap
    if hasattr(value, "value"):
        inner = value.value
        # numpy array
        if hasattr(inner, "tolist"):
            inner = inner.tolist()
        # Flatten single-element nested lists like [[55.0]]
        while isinstance(inner, list) and len(inner) == 1:
            inner = inner[0]
        return inner
    # Plain numpy scalar / array
    if hasattr(value, "tolist"):
        v = value.tolist()
        while isinstance(v, list) and len(v) == 1:
            v = v[0]
        return v
    return value


# ---------------------------------------------------------------------------
# Tool 1 — List sheets
# ---------------------------------------------------------------------------

async def list_sheets(
    file_path: str,
    tool_context=None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """List all sheet names in an Excel workbook.

    Args:
        file_path: Absolute path to the .xlsx file.
    """
    log.info("[ExcelTools:list_sheets] Opening %s", file_path)
    try:
        wb = _open_workbook(file_path)
        sheets = _sheet_names(wb)
        wb.close()
        return {
            "status": "success",
            "file": file_path,
            "sheets": sheets,
            "sheet_count": len(sheets),
        }
    except Exception as exc:
        log.error("[ExcelTools:list_sheets] %s", exc)
        return {"status": "error", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 2 — Read a range
# ---------------------------------------------------------------------------

async def read_range(
    file_path: str,
    sheet_name: Optional[str] = None,
    range_address: Optional[str] = None,
    max_rows: int = 200,
    include_formulas: bool = False,
    tool_context=None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Read cell values (and optionally formulas) from an Excel range.

    Args:
        file_path: Absolute path to the .xlsx file.
        sheet_name: Sheet to read. Defaults to the active sheet.
        range_address: Excel range like 'A1:D10'. If omitted, reads the
            entire used range (up to *max_rows* rows).
        max_rows: Maximum number of rows to return (default 200).
        include_formulas: When True the response includes the raw formula
            strings alongside computed values.
    """
    log.info("[ExcelTools:read_range] %s sheet=%s range=%s", file_path, sheet_name, range_address)
    try:
        wb_values = _open_workbook(file_path, data_only=True)
        ws_values = wb_values[sheet_name] if sheet_name else wb_values.active

        wb_formulas = None
        ws_formulas = None
        if include_formulas:
            wb_formulas = _open_workbook(file_path, data_only=False)
            ws_formulas = wb_formulas[sheet_name] if sheet_name else wb_formulas.active

        if range_address:
            cells = ws_values[range_address]
        else:
            cells = ws_values.iter_rows(
                min_row=ws_values.min_row,
                max_row=min(ws_values.max_row or 1, (ws_values.min_row or 1) + max_rows - 1),
                min_col=ws_values.min_column,
                max_col=ws_values.max_column,
            )

        rows: List[List[Any]] = []
        formula_rows: List[List[Any]] = []
        for row in cells:
            # openpyxl returns a tuple for a single-cell range
            if not hasattr(row, "__iter__"):
                row = (row,)
            rows.append([_serialize_cell(c) for c in row])
            if include_formulas and ws_formulas:
                f_row = []
                for c in row:
                    fc = ws_formulas.cell(row=c.row, column=c.column)
                    val = fc.value
                    f_row.append(val if isinstance(val, str) and val.startswith("=") else None)
                formula_rows.append(f_row)

        wb_values.close()
        if wb_formulas:
            wb_formulas.close()

        result: Dict[str, Any] = {
            "status": "success",
            "file": file_path,
            "sheet": sheet_name or ws_values.title,
            "rows": rows,
            "row_count": len(rows),
        }
        if include_formulas:
            result["formulas"] = formula_rows
        return result

    except Exception as exc:
        log.error("[ExcelTools:read_range] %s", exc)
        return {"status": "error", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 3 — Get formulas
# ---------------------------------------------------------------------------

async def get_formulas(
    file_path: str,
    sheet_name: Optional[str] = None,
    range_address: Optional[str] = None,
    tool_context=None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Extract all formulas from a sheet or range.

    Returns a mapping of cell references to their formula strings.

    Args:
        file_path: Absolute path to the .xlsx file.
        sheet_name: Sheet to inspect. Defaults to the active sheet.
        range_address: Optional range like 'A1:D10'. If omitted, scans
            the entire used range.
    """
    log.info("[ExcelTools:get_formulas] %s sheet=%s range=%s", file_path, sheet_name, range_address)
    try:
        wb = _open_workbook(file_path, data_only=False)
        ws = wb[sheet_name] if sheet_name else wb.active

        if range_address:
            cells = ws[range_address]
        else:
            cells = ws.iter_rows(
                min_row=ws.min_row,
                max_row=ws.max_row,
                min_col=ws.min_column,
                max_col=ws.max_column,
            )

        formulas_map: Dict[str, str] = {}
        for row in cells:
            if not hasattr(row, "__iter__"):
                row = (row,)
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    formulas_map[_cell_ref(cell.row, cell.column)] = cell.value

        wb.close()
        return {
            "status": "success",
            "file": file_path,
            "sheet": sheet_name or ws.title,
            "formulas": formulas_map,
            "formula_count": len(formulas_map),
        }
    except Exception as exc:
        log.error("[ExcelTools:get_formulas] %s", exc)
        return {"status": "error", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 4 — Evaluate formulas
# ---------------------------------------------------------------------------

async def evaluate_formulas(
    file_path: str,
    cells: Optional[List[str]] = None,
    sheet_name: Optional[str] = None,
    tool_context=None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate Excel formulas in the workbook and return computed results.

    Uses the *formulas* library to reproduce Excel's calculation engine
    in pure Python.  Every formula in the workbook is resolved using the
    data present in the file — no Excel installation required.

    Args:
        file_path: Absolute path to the .xlsx file.
        cells: Optional list of cell references to evaluate
            (e.g. ``["C2", "D5"]``).  If omitted, all formulas in the
            target sheet are evaluated.
        sheet_name: Sheet containing the formulas. Defaults to the
            first sheet.
    """
    log.info("[ExcelTools:evaluate_formulas] %s cells=%s", file_path, cells)
    try:
        xl_model = formulas.ExcelModel().loads(file_path).finish()
        solution = xl_model.calculate()

        results: Dict[str, Any] = {}
        target_sheet = sheet_name

        for key, value in solution.items():
            # Keys look like "'Sheet1'!A1" or "'Sheet1'!A1:B3"
            parts = str(key).split("!")
            if len(parts) == 2:
                s_name = parts[0].strip("'\"")
                cell_addr = parts[1]
            else:
                s_name = None
                cell_addr = str(key)

            if target_sheet and s_name and s_name.lower() != target_sheet.lower():
                continue

            val = _unwrap_value(value)

            if cells:
                if cell_addr.upper() in [c.upper() for c in cells]:
                    results[cell_addr] = val
            else:
                results[cell_addr] = val

        return {
            "status": "success",
            "file": file_path,
            "sheet": target_sheet,
            "results": results,
            "evaluated_count": len(results),
        }
    except Exception as exc:
        log.error("[ExcelTools:evaluate_formulas] %s", exc)
        return {"status": "error", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 5 — Recalculate with new inputs
# ---------------------------------------------------------------------------

async def recalculate(
    file_path: str,
    inputs: Dict[str, Any] = None,
    output_cells: Optional[List[str]] = None,
    sheet_name: Optional[str] = None,
    tool_context=None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Change input values and recalculate the spreadsheet.

    This is the key "what-if" tool: inject new values into specific cells,
    then re-evaluate all formulas and return the updated outputs.

    Args:
        file_path: Absolute path to the .xlsx file.
        inputs: Mapping of cell references to new values,
            e.g. ``{"B2": 100, "B3": 200}``.  Cell references may
            optionally include the sheet name (``"'Sheet1'!B2"``).
        output_cells: Optional list of cell references whose
            recalculated values should be returned.  If omitted, all
            formula cells are returned.
        sheet_name: Default sheet name used when cell references in
            *inputs* / *output_cells* do not include a sheet qualifier.
    """
    log.info("[ExcelTools:recalculate] %s inputs=%s outputs=%s", file_path, inputs, output_cells)
    if not inputs:
        return {"status": "error", "message": "inputs parameter is required"}

    try:
        xl_model = formulas.ExcelModel().loads(file_path).finish()

        # The formulas library uses keys like "'[filename]SHEETNAME'!CELL"
        filename = os.path.basename(file_path)
        wb = _open_workbook(file_path)
        default_sheet = sheet_name or wb.sheetnames[0]
        wb.close()

        qualified_inputs = {}
        for ref, val in inputs.items():
            if "!" in ref:
                # User provided sheet-qualified ref; ensure filename prefix
                if "[" not in ref:
                    parts = ref.split("!")
                    s = parts[0].strip("'\"").upper()
                    c = parts[1].upper()
                    qualified_inputs[f"'[{filename}]{s}'!{c}"] = val
                else:
                    qualified_inputs[ref] = val
            else:
                qualified_inputs[
                    f"'[{filename}]{default_sheet.upper()}'!{ref.upper()}"
                ] = val

        solution = xl_model.calculate(inputs=qualified_inputs)

        results: Dict[str, Any] = {}
        for key, value in solution.items():
            parts = str(key).split("!")
            cell_addr = parts[1] if len(parts) == 2 else str(key)
            val = _unwrap_value(value)

            if output_cells:
                if cell_addr.upper() in [c.upper() for c in output_cells]:
                    results[cell_addr] = val
            else:
                results[cell_addr] = val

        return {
            "status": "success",
            "file": file_path,
            "inputs_applied": inputs,
            "results": results,
            "evaluated_count": len(results),
        }
    except Exception as exc:
        log.error("[ExcelTools:recalculate] %s", exc)
        return {"status": "error", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 6 — Analyze / summarize a sheet
# ---------------------------------------------------------------------------

async def analyze_sheet(
    file_path: str,
    sheet_name: Optional[str] = None,
    tool_context=None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a structural summary of a sheet.

    Includes dimensions, column headers, data types per column,
    formula locations, and basic statistics for numeric columns.

    Args:
        file_path: Absolute path to the .xlsx file.
        sheet_name: Sheet to analyze. Defaults to the active sheet.
    """
    log.info("[ExcelTools:analyze_sheet] %s sheet=%s", file_path, sheet_name)
    try:
        wb_vals = _open_workbook(file_path, data_only=True)
        ws_vals = wb_vals[sheet_name] if sheet_name else wb_vals.active

        wb_fmls = _open_workbook(file_path, data_only=False)
        ws_fmls = wb_fmls[sheet_name] if sheet_name else wb_fmls.active

        min_r, max_r = ws_vals.min_row or 1, ws_vals.max_row or 1
        min_c, max_c = ws_vals.min_column or 1, ws_vals.max_column or 1

        # Headers (first row)
        headers = []
        for col in range(min_c, max_c + 1):
            val = ws_vals.cell(row=min_r, column=col).value
            headers.append(str(val) if val is not None else f"Col{col}")

        # Per-column info
        columns_info = []
        for ci, col in enumerate(range(min_c, max_c + 1)):
            nums = []
            types_seen = set()
            formula_count = 0
            for row in range(min_r + 1, max_r + 1):
                v = ws_vals.cell(row=row, column=col).value
                fv = ws_fmls.cell(row=row, column=col).value
                if isinstance(fv, str) and fv.startswith("="):
                    formula_count += 1
                if v is not None:
                    types_seen.add(type(v).__name__)
                    if isinstance(v, (int, float)):
                        nums.append(v)

            info: Dict[str, Any] = {
                "header": headers[ci],
                "column_letter": get_column_letter(col),
                "data_types": sorted(types_seen),
                "formula_count": formula_count,
            }
            if nums:
                info["numeric_stats"] = {
                    "count": len(nums),
                    "min": min(nums),
                    "max": max(nums),
                    "sum": round(sum(nums), 6),
                    "average": round(sum(nums) / len(nums), 6),
                }
            columns_info.append(info)

        # Collect all formula locations
        all_formulas: Dict[str, str] = {}
        for row in ws_fmls.iter_rows(min_row=min_r, max_row=max_r, min_col=min_c, max_col=max_c):
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    all_formulas[_cell_ref(cell.row, cell.column)] = cell.value

        wb_vals.close()
        wb_fmls.close()

        return {
            "status": "success",
            "file": file_path,
            "sheet": ws_vals.title,
            "dimensions": {
                "rows": max_r - min_r + 1,
                "columns": max_c - min_c + 1,
                "data_rows": max_r - min_r,  # excluding header
            },
            "headers": headers,
            "columns": columns_info,
            "formulas": all_formulas,
            "formula_count": len(all_formulas),
        }
    except Exception as exc:
        log.error("[ExcelTools:analyze_sheet] %s", exc)
        return {"status": "error", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 7 — Write cells
# ---------------------------------------------------------------------------

async def write_cells(
    file_path: str,
    updates: Dict[str, Any] = None,
    sheet_name: Optional[str] = None,
    save_as: Optional[str] = None,
    tool_context=None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Write values or formulas to specific cells and save the workbook.

    Args:
        file_path: Absolute path to the .xlsx file to modify.
        updates: Mapping of cell references to values or formula strings,
            e.g. ``{"A1": "Name", "B2": 42, "C2": "=A2+B2"}``.
        sheet_name: Target sheet. Defaults to the active sheet.
        save_as: Optional path to save as a new file instead of
            overwriting the original.
    """
    log.info("[ExcelTools:write_cells] %s updates=%s", file_path, updates)
    if not updates:
        return {"status": "error", "message": "updates parameter is required"}

    try:
        wb = _open_workbook(file_path, data_only=False)
        ws = wb[sheet_name] if sheet_name else wb.active

        written = []
        for ref, val in updates.items():
            ws[ref] = val
            written.append(ref)

        out_path = save_as or file_path
        wb.save(out_path)
        wb.close()

        return {
            "status": "success",
            "file": out_path,
            "cells_written": written,
            "count": len(written),
        }
    except Exception as exc:
        log.error("[ExcelTools:write_cells] %s", exc)
        return {"status": "error", "message": str(exc)}


# ---------------------------------------------------------------------------
# Tool 8 — Create a new workbook
# ---------------------------------------------------------------------------

async def create_workbook(
    file_path: str,
    sheet_name: str = "Sheet1",
    headers: Optional[List[str]] = None,
    rows: Optional[List[List[Any]]] = None,
    tool_context=None,
    tool_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a new Excel workbook with optional initial data.

    Args:
        file_path: Where to save the new .xlsx file.
        sheet_name: Name of the initial sheet (default "Sheet1").
        headers: Optional list of column header strings.
        rows: Optional list of data rows (each row is a list of values).
    """
    log.info("[ExcelTools:create_workbook] %s", file_path)
    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_name

        current_row = 1
        if headers:
            for ci, h in enumerate(headers, start=1):
                ws.cell(row=current_row, column=ci, value=h)
            current_row += 1

        if rows:
            for row_data in rows:
                for ci, val in enumerate(row_data, start=1):
                    ws.cell(row=current_row, column=ci, value=val)
                current_row += 1

        wb.save(file_path)
        wb.close()

        return {
            "status": "success",
            "file": file_path,
            "sheet": sheet_name,
            "rows_written": (current_row - 1),
        }
    except Exception as exc:
        log.error("[ExcelTools:create_workbook] %s", exc)
        return {"status": "error", "message": str(exc)}
