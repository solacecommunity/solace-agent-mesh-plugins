# Finance SAM Plugin

A Solace Agent Mesh plugin that provides real-time stock price and fundamental financial data using yfinance.

---

**Plugin Type:** `Custom Code Agent`

> **Note:** This is a community-contributed plugin for [Solace Agent Mesh](https://solacelabs.github.io/solace-agent-mesh/) and is not officially supported by Solace. For community support, please open an issue in this repository.

---

## Overview

The Finance agent enables natural language queries about stock market data by wrapping the [yfinance](https://pypi.org/project/yfinance/) library. It can retrieve live price data and key fundamental metrics for any publicly traded stock using its ticker symbol.

This agent is well-suited for financial dashboards, investment research workflows, and conversational finance applications built on Solace Agent Mesh.

## Features

This agent provides the following capabilities:

- **Stock Price Lookup**: Get the current price, day change (absolute and percent), daily high/low, volume, and 52-week range for any ticker symbol
- **Fundamental Analysis**: Retrieve key financial metrics including P/E ratio, market cap, EPS, dividend yield, revenue, profit margins, and debt-to-equity ratio
- **Company Context**: Includes company name, sector, and industry with every fundamentals query

## Configuration

This plugin does not require any API keys. It uses the free [yfinance](https://pypi.org/project/yfinance/) library to fetch publicly available market data.

### Configuration File (`config.yaml`)

The `config.yaml` in this plugin serves as a template. When you use `sam plugin add <component_name> --plugin finance`, the following placeholders in the YAML structure will be replaced with variations of `<component_name>`:
- `__COMPONENT_UPPER_SNAKE_CASE_NAME__`
- `__COMPONENT_KEBAB_CASE_NAME__`
- `__COMPONENT_PASCAL_CASE_NAME__`

Customize the `config.yaml` in this plugin directory to define the base configuration for components created from it.

## Installation

To add this plugin to your Solace Agent Mesh project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=finance
```

This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.

Alternatively, you can install via the Solace Agent Mesh Plugin Catalog:

1. Launch the plugin catalog: `sam plugin catalog`
2. Add this repository if you have not done so already: `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the plugin using the install button in the GUI or with: `sam plugin add finance --plugin finance`

## Usage

Once the agent is running, you can interact with it through the Solace Agent Mesh orchestrator using natural language prompts.

### Example Prompts

#### Stock Prices
- *"What is the current price of Apple stock?"*
- *"How much has Tesla's stock moved today?"*
- *"What is MSFT trading at right now?"*

#### Fundamentals
- *"What is the P/E ratio for Amazon?"*
- *"Show me the market cap and dividend yield for Coca-Cola"*
- *"What are the profit margins for NVIDIA?"*

#### Combined Analysis
- *"Give me an overview of Google's stock including price and key fundamentals"*
- *"Compare the EPS and revenue for Apple and Microsoft"*

### Tools Available

The agent exposes the following tools:

- **`get_stock_price`**: Returns current price, previous close, day change (value and percent), daily high/low, volume, and 52-week high/low for a given ticker symbol
- **`get_stock_fundamentals`**: Returns company name, sector, industry, market cap, P/E ratio, forward P/E, EPS, dividend yield, revenue, profit margin, operating margin, debt-to-equity ratio, return on equity, and book value

## External Services

This plugin utilizes the following external service:

- **[Yahoo Finance via yfinance](https://pypi.org/project/yfinance/)**: Provides publicly available stock price and fundamental data. No API key is required, but usage is subject to Yahoo Finance's terms of service.

## Limitations

- **Market Hours**: Price data reflects the most recent trading session; real-time streaming is not supported
- **Data Availability**: Some fundamental metrics may not be available for all tickers (e.g., ETFs, foreign-listed stocks)
- **Rate Limits**: Yahoo Finance may throttle requests under heavy usage
- **Ticker Format**: Symbols must match Yahoo Finance's ticker format (e.g., `BRK-B` not `BRK.B`)

---

## Original Author

Created by Greg Meldrum <greg.meldrum@solace.com>

## Contributing

To contribute to this plugin review [Contributing](/CONTRIBUTING.md)

---

## License

See project license.
