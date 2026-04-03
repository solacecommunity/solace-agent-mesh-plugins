"""Excel Tools SAM Plugin Package

Read, write, analyze, and reproduce calculations in Excel spreadsheets
through Solace Agent Mesh.
"""

__version__ = "0.1.0"
__author__ = "Raphael Caillon"

from .tools import (
    list_sheets,
    read_range,
    get_formulas,
    evaluate_formulas,
    recalculate,
    analyze_sheet,
    write_cells,
    create_workbook,
)

__all__ = [
    "list_sheets",
    "read_range",
    "get_formulas",
    "evaluate_formulas",
    "recalculate",
    "analyze_sheet",
    "write_cells",
    "create_workbook",
]
