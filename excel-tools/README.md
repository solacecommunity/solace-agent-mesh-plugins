# Excel Tools SAM Plugin

Read, write, analyze, and reproduce calculations in Excel spreadsheets (.xlsx) through natural language — no Microsoft Excel required.

---

**Plugin Type:** `Custom Code Agent`

> **Note:** This is a community-contributed plugin for [Solace Agent Mesh (SAM)](https://github.com/SolaceLabs/solace-agent-mesh) and is not officially supported by Solace. For community support, please open an issue in this repository.
> ⭐️ Please leave a star on the [Solace Agent Mesh (SAM)](https://github.com/SolaceLabs/solace-agent-mesh) repo while you are there.

---

## Overview

The Excel Tools plugin gives any SAM agent the ability to work with Excel workbooks as easily as a human analyst. Point it at a `.xlsx` file and it can read data, inspect formulas, run the full calculation chain in pure Python, and even perform "what-if" scenarios by swapping input values and recalculating outputs.

This is especially useful for agents that need to:
- Ingest financial models, budgets, or operational spreadsheets and answer questions about them.
- Reproduce and verify Excel calculations without an Excel installation.
- Generate or modify workbooks programmatically as part of a larger workflow.

## Features

- **Read & Browse**: List sheets, read arbitrary ranges, and get a structural overview of any workbook.
- **Formula Extraction**: See every formula in the workbook with its cell address.
- **Pure-Python Evaluation**: Evaluate the entire formula dependency graph using the [formulas](https://pypi.org/project/formulas/) library — no Excel or LibreOffice needed.
- **What-If Recalculation**: Change input cells and instantly see how outputs change across the spreadsheet.
- **Write & Create**: Update existing cells or create brand-new workbooks with headers and data.
- **Sheet Analysis**: Get column types, numeric statistics (min/max/sum/avg), and a formula map in one call.

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

- *"Open budget_2025.xlsx and show me a summary of the first sheet."*
- *"What formulas are in the Revenue sheet?"*
- *"Evaluate all the formulas in quarterly_report.xlsx and show me the results."*
- *"What happens to total profit if I change cell B5 (unit price) to 29.99?"*
- *"Create a new workbook with columns Name, Quantity, Price and add three sample rows."*
- *"Write the formula =SUM(B2:B10) into cell B11 of my file."*

### Tools Available

| Tool | Description |
|---|---|
| **`list_sheets`** | List all sheet names in a workbook. |
| **`read_range`** | Read cell values (and optionally formulas) from a range or full sheet. |
| **`get_formulas`** | Extract every formula string with its cell address. |
| **`evaluate_formulas`** | Evaluate all formulas in pure Python and return computed values. |
| **`recalculate`** | Change input cells and recalculate — the core "what-if" tool. |
| **`analyze_sheet`** | Structural summary: dimensions, headers, column types, statistics, formula map. |
| **`write_cells`** | Write values or formulas to specific cells and save. |
| **`create_workbook`** | Create a new `.xlsx` workbook with optional headers and data. |

## Dependencies

This plugin uses the following Python libraries (installed automatically):

- **[openpyxl](https://openpyxl.readthedocs.io/)** — Read and write `.xlsx` files, inspect formulas and cell metadata.
- **[formulas](https://formulas.readthedocs.io/)** — Pure-Python Excel formula parser and evaluator that reproduces the Excel calculation engine.

## Limitations

- Only `.xlsx` files are supported (not `.xls`, `.csv`, or `.xlsb`).
- Formula evaluation covers most common Excel functions but may not support every obscure function — see the [formulas library docs](https://formulas.readthedocs.io/) for the supported function list.
- Very large workbooks (100k+ rows) may be slow to evaluate; use `range_address` and `max_rows` parameters to limit scope.
- Macros (VBA) are not executed.

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

### Version 0.1.0
- Initial release with 8 tools: list_sheets, read_range, get_formulas, evaluate_formulas, recalculate, analyze_sheet, write_cells, create_workbook.
