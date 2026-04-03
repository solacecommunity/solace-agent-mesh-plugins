# Excel Tools SAM Plugin

Read, write, analyze, automate, and reproduce calculations in Excel spreadsheets (.xlsx) through natural language — no Microsoft Excel required. Includes cron-style scheduled recalculation, batch scenario analysis, template stamping, and more.

---

**Plugin Type:** `Custom Code Agent`

> **Note:** This is a community-contributed plugin for [Solace Agent Mesh (SAM)](https://github.com/SolaceLabs/solace-agent-mesh) and is not officially supported by Solace. For community support, please open an issue in this repository.
> ⭐️ Please leave a star on the [Solace Agent Mesh (SAM)](https://github.com/SolaceLabs/solace-agent-mesh) repo while you are there.

---

## Overview

The Excel Tools plugin gives any SAM agent the ability to work with Excel workbooks as easily as a human analyst. Point it at a `.xlsx` file and it can read data, inspect formulas, run the full calculation chain in pure Python, and even perform "what-if" scenarios by swapping input values and recalculating outputs.

Beyond one-shot analysis, the plugin supports **automation workflows**: schedule recurring recalculations on a timer, run batch sensitivity analyses across dozens of scenarios, stamp templates to produce filled reports, diff two versions of a workbook, validate formulas for errors, export data to JSON for downstream pipelines, and freeze formulas into a point-in-time snapshot.

This is especially useful for agents that need to:
- Ingest financial models, budgets, or operational spreadsheets and answer questions about them.
- Reproduce and verify Excel calculations without an Excel installation.
- Automate recurring reports — recalculate a pricing model every hour and persist the results.
- Run sensitivity analysis across multiple input scenarios in a single call.
- Generate or modify workbooks programmatically as part of a larger workflow.

## Features

### Core
- **Read & Browse**: List sheets, read arbitrary ranges, and get a structural overview of any workbook.
- **Formula Extraction**: See every formula in the workbook with its cell address.
- **Pure-Python Evaluation**: Evaluate the entire formula dependency graph using the [formulas](https://pypi.org/project/formulas/) library — no Excel or LibreOffice needed.
- **What-If Recalculation**: Change input cells and instantly see how outputs change across the spreadsheet.
- **Write & Create**: Update existing cells or create brand-new workbooks with headers and data.
- **Sheet Analysis**: Get column types, numeric statistics (min/max/sum/avg), and a formula map in one call.

### Scheduling & Cron Jobs
- **Scheduled Recalculation**: Set up a recurring job that re-evaluates a workbook at a fixed interval (e.g. every 5 minutes, every hour). Optionally inject new inputs each cycle and persist results to a separate audit workbook.
- **Job Management**: List all active scheduled jobs with run history, or cancel them by ID.

### Advanced Automation
- **Batch Scenario Analysis**: Run multiple what-if scenarios in one call — ideal for sensitivity analysis, pricing tiers, or Monte Carlo inputs.
- **Copy Sheet**: Duplicate a sheet within the same workbook or copy it to a different file.
- **Template Stamping**: Copy a template workbook, fill in specified cells with new data, and save — formulas are preserved for downstream evaluation.
- **Workbook Diff**: Compare two workbooks cell-by-cell and get a structured list of every difference.
- **Formula Validation**: Check every formula for Excel error values (#REF!, #DIV/0!, #NAME?, #VALUE!, #N/A, #NULL!, #NUM!) and report issues.
- **JSON Export**: Export sheet data as JSON in records, columns, or rows format for pipeline integration.
- **Formula Snapshot**: Replace all formulas with their computed values to create a frozen point-in-time copy (useful for archiving or sharing without exposing formulas).

## Configuration

No additional environment variables are required beyond the standard SAM configuration. The plugin works with local `.xlsx` files accessible from the agent's filesystem.

### Configuration File (`config.yaml`)

The `config.yaml` in this plugin serves as a template. When you use `sam plugin add <component_name> --plugin excel-tools`, the following placeholders will be replaced:
- `__COMPONENT_UPPER_SNAKE_CASE_NAME__`
- `__COMPONENT_KEBAB_CASE_NAME__`
- `__COMPONENT_PASCAL_CASE_NAME__`

## Installation

```bash
sam plugin add <your-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=excel-tools
```

This creates a new component configuration at `configs/plugins/<your-component-name>.yaml`.

Alternatively, install via the SAM Plugin Catalog:

1. Launch the catalog: `sam plugin catalog`
2. Add this repository if needed: **+ Add Registry** → paste `https://github.com/solacecommunity/solace-agent-mesh-plugins` with name `Community`
3. Install the plugin and configure as needed.

## Usage

Once the agent is running, interact with it through the SAM orchestrator using natural language.

### Example Prompts

**Core:**
- *"Open budget_2025.xlsx and show me a summary of the first sheet."*
- *"What formulas are in the Revenue sheet?"*
- *"Evaluate all the formulas in quarterly_report.xlsx and show me the results."*
- *"What happens to total profit if I change cell B5 (unit price) to 29.99?"*
- *"Create a new workbook with columns Name, Quantity, Price and add three sample rows."*

**Scheduling:**
- *"Recalculate pricing_model.xlsx every 30 minutes and save results to pricing_history.xlsx."*
- *"Show me all running scheduled jobs."*
- *"Cancel the scheduled job with ID abc123."*

**Automation:**
- *"Run three scenarios on the forecast: low (B2=100), mid (B2=250), high (B2=500) and compare the net profit in D10."*
- *"Copy the Q1 sheet to a new file called q1_archive.xlsx."*
- *"Use invoice_template.xlsx as a template — fill in B2 with 'Acme Corp' and C5 with 42000, and save as acme_invoice.xlsx."*
- *"Compare last_month.xlsx and this_month.xlsx and show me what changed."*
- *"Check all formulas in the Budget sheet for errors."*
- *"Export the Sales sheet to JSON."*
- *"Create a snapshot of financial_model.xlsx with all formulas replaced by their values."*

### Tools Available

| Tool | Category | Description |
|---|---|---|
| **`list_sheets`** | Core | List all sheet names in a workbook. |
| **`read_range`** | Core | Read cell values (and optionally formulas) from a range or full sheet. |
| **`get_formulas`** | Core | Extract every formula string with its cell address. |
| **`evaluate_formulas`** | Core | Evaluate all formulas in pure Python and return computed values. |
| **`recalculate`** | Core | Change input cells and recalculate — the core "what-if" tool. |
| **`analyze_sheet`** | Core | Structural summary: dimensions, headers, column types, statistics, formula map. |
| **`write_cells`** | Core | Write values or formulas to specific cells and save. |
| **`create_workbook`** | Core | Create a new `.xlsx` workbook with optional headers and data. |
| **`schedule_recalculation`** | Scheduling | Set up a recurring recalculation job at a fixed interval. |
| **`list_scheduled_jobs`** | Scheduling | List all active scheduled jobs with run counts and history. |
| **`cancel_scheduled_job`** | Scheduling | Cancel a running scheduled job by ID. |
| **`batch_recalculate`** | Automation | Run multiple what-if scenarios in one call. |
| **`copy_sheet`** | Automation | Duplicate a sheet within or across workbooks. |
| **`apply_template`** | Automation | Fill a template workbook with new data and save a copy. |
| **`diff_workbooks`** | Automation | Compare two workbooks cell-by-cell and return differences. |
| **`validate_formulas`** | Automation | Check formulas for errors (#REF!, #DIV/0!, etc.). |
| **`export_sheet_to_json`** | Automation | Export sheet data as JSON (records, columns, or rows). |
| **`snapshot_formulas`** | Automation | Replace all formulas with computed values for a frozen copy. |

## Dependencies

This plugin uses the following Python libraries (installed automatically):

- **[openpyxl](https://openpyxl.readthedocs.io/)** — Read and write `.xlsx` files, inspect formulas and cell metadata.
- **[formulas](https://formulas.readthedocs.io/)** — Pure-Python Excel formula parser and evaluator that reproduces the Excel calculation engine.

## Limitations

- Only `.xlsx` files are supported (not `.xls`, `.csv`, or `.xlsb`).
- Formula evaluation covers most common Excel functions but may not support every obscure function — see the [formulas library docs](https://formulas.readthedocs.io/) for the supported function list.
- Very large workbooks (100k+ rows) may be slow to evaluate; use `range_address` and `max_rows` parameters to limit scope.
- Macros (VBA) are not executed.
- Scheduled jobs run as in-process daemon threads and do not survive agent restarts. For persistent scheduling, use an external scheduler that invokes the agent.

## Building and Running

### Prerequisites

- Python >= 3.10
- SAM installed and configured

### Development

```bash
cd excel-tools
pip install -e ".[test]"
pytest
```

---

## Original Author

Created by [Raphael Caillon](https://github.com/raphael-solace)

## Contributing

To contribute to this plugin review [Contributing](/CONTRIBUTING.md)

---

## Changelog

### Version 0.2.0
- Added scheduled recalculation (cron jobs): `schedule_recalculation`, `list_scheduled_jobs`, `cancel_scheduled_job`.
- Added batch scenario analysis: `batch_recalculate`.
- Added sheet copy (same or cross-workbook): `copy_sheet`.
- Added template stamping: `apply_template`.
- Added workbook diff: `diff_workbooks`.
- Added formula validation: `validate_formulas`.
- Added JSON export: `export_sheet_to_json`.
- Added formula snapshot (freeze to values): `snapshot_formulas`.

### Version 0.1.0
- Initial release with 8 tools: list_sheets, read_range, get_formulas, evaluate_formulas, recalculate, analyze_sheet, write_cells, create_workbook.
