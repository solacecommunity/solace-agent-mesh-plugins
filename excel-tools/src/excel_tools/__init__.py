"""Excel Tools SAM Plugin Package

Read, write, analyze, and reproduce calculations in Excel spreadsheets
through Solace Agent Mesh.  Includes scheduled recalculation (cron jobs),
batch scenario analysis, template stamping, workbook diffing, and more.
"""

__version__ = "0.3.0"
__author__ = "Raphael Caillon"

from .tools import (
    # Core tools (v0.1)
    list_sheets,
    read_range,
    get_formulas,
    evaluate_formulas,
    recalculate,
    analyze_sheet,
    write_cells,
    create_workbook,
    # Scheduling / cron (v0.2)
    schedule_recalculation,
    list_scheduled_jobs,
    cancel_scheduled_job,
    # Advanced automation (v0.2)
    batch_recalculate,
    copy_sheet,
    apply_template,
    diff_workbooks,
    validate_formulas,
    export_sheet_to_json,
    snapshot_formulas,
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
    "schedule_recalculation",
    "list_scheduled_jobs",
    "cancel_scheduled_job",
    "batch_recalculate",
    "copy_sheet",
    "apply_template",
    "diff_workbooks",
    "validate_formulas",
    "export_sheet_to_json",
    "snapshot_formulas",
]
