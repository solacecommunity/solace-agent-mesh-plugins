# Sample Prompts for Excel Tools Agent

Use these prompts with the included `sample_sales_dashboard.xlsx` workbook.

## Getting Started

> Analyze the Sales sheet in the uploaded file and give me an overview.

> List all sheets in this workbook.

## Reading Data

> Read the full Sales sheet and show me the data.

> Show me just the revenue and profit columns (H and J) from the Sales sheet.

> Read range A1:F6 from the Sales sheet.

## Working with Formulas

> What formulas are used in the Sales sheet?

> Evaluate all formulas in the workbook and show me the computed results.

> Show me the formulas in the Projections sheet and explain what they calculate.

## What-If / Scenario Analysis

> What happens to Widget A's revenue if we increase the unit price from $24.99 to $34.99? (Hint: change cell G2 in the Sales sheet)

> Run a what-if: set the growth rate (Projections!B3) to 25% and show me the projected Year 3 revenue.

> Compare three scenarios for the growth rate (Projections!B3): 10%, 20%, and 30%. Show me the Year 3 after-tax revenue for each.

## Expense Analysis

> Analyze the Expenses sheet. Which category has the highest total?

> Export the Expenses sheet to JSON format.

> What percentage of total expenses goes to Salaries?

## Modifying Data

> Create a copy of the Sales sheet called "Sales_Backup" in the same workbook.

> Add a new row for "Deluxe W" with Q1=40, Q2=55, Q3=60, Q4=75, price $149.99, cost $65.00 to the Sales sheet.

## Validation & Comparison

> Validate all formulas in the workbook for errors.

> Create a snapshot of the workbook with all formulas replaced by their computed values.

## Advanced Automation

> Schedule a recalculation of the workbook every 5 minutes and save results to a tracking file.

> Apply the workbook as a template: fill B3 (growth rate) with 0.20 and B4 (tax rate) with 0.25, and save as "projected_scenario.xlsx".
