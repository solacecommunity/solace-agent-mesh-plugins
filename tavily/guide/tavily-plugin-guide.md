# Tavily Plugin for Solace Agent Mesh

## Overview

The Tavily plugin enables Solace Agent Mesh (SAM) to perform AI-powered web searches using Tavily's intelligent search API. This plugin provides enhanced search capabilities with AI-driven result processing, making it easy to find and analyze relevant information from across the web.

## What is Tavily?

[Tavily](https://www.tavily.com/) is an AI-powered search API designed for intelligent applications. It provides:
- Real-time web search with AI processing
- Intelligent result filtering and ranking
- Context-aware search optimization
- Structured search result delivery
- Advanced query understanding

## Plugin Details

- **Plugin Name**: `tavily`
- **Version**: 0.1.0
- **Author**: Jamieson Walker <jamieson.walker@solace.com>
- **Repository**: [Solace Community Plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins)

## Capabilities

This plugin provides SAM with the following capabilities:

### 🧠 AI-Powered Search
- Intelligent query processing and optimization
- Context-aware search result ranking
- Natural language query understanding
- Advanced semantic search capabilities

### 🔍 Real-Time Web Discovery
- Access to current web content and information
- Real-time data collection from multiple sources
- Dynamic result processing and filtering
- Fresh content prioritization

### 📊 Structured Result Processing
- Organized search result presentation
- Relevance scoring and ranking
- Content summarization and extraction
- Multi-format result delivery

### 🎯 Contextual Analysis
- Understanding search intent and context
- Related topic discovery
- Trend analysis and insights
- Comprehensive information gathering

## How It Works

The Tavily plugin integrates with SAM using the **MCP (Model Context Protocol)** wrapper pattern. This means:

1. **Plugin Configuration**: The plugin is defined in a `config.yaml` file that serves both as metadata and SAM agent configuration
2. **MCP Integration**: The plugin communicates with Tavily's API through a standardized interface
3. **Natural Language Interface**: Users can perform complex searches using natural language queries through SAM
4. **Tool Abstraction**: Advanced search operations are abstracted into simple, conversational commands

## Prerequisites

Before using this plugin, you need:

1. **Solace Agent Mesh v1**: Ensure you have SAM installed and configured
2. **Tavily Account**: Sign up for a [Tavily account](https://www.tavily.com/)
3. **API Key**: Obtain your Tavily API key from your account dashboard
4. **Python Environment**: Ensure you have a proper Python environment set up

## Installation and Setup

### Step 1: Add the Community Plugin Repository

1. Run `sam plugin catalog` from your python virtual environment and inside your SAM directory.
2. Add the Solace Community Plugin repository:
   ![SAM Community Plugin Repository add](./assets/samCommunityRepoAdd.png)
   ```bash 
   https://github.com/solacecommunity/solace-agent-mesh-plugins
   ```
   
   ![SAM Community Plugin Repository](./assets/samCommunityRepo.png)

### Step 2: Install the Plugin in SAM

Use SAM's plugin installation mechanism to install the Bright Data plugin with the gui or the CLI:

*GUI* 

![Tavily Install Gui](./assets/samTavilyInstall.png)

*CLI*
```bash
sam plugin add tavily --plugin tavily
```
### Step 3: Configure Environment Variables

Set up your Tavily API credentials as environment variables:

```bash
export TAVILY_TOKEN="your_api_key_here"
```
### Step 4: Verify Installation

Check that the plugin is properly installed and recognized by SAM:

```bash
sam run
```

Select agent page. You should see `tavily` agent in the list of available agents.
![Tavily Installed](./assets/samTavilyInstalled.png)

## Usage Examples

Once installed, you can interact with the Tavily plugin through natural language queries in SAM:

### Market Research
```
"Search for the latest trends in sustainable technology and renewable energy"
```

### Competitive Intelligence
```
"Find recent news and developments about AI startups in the healthcare sector"
```

### Technical Information
```
"Search for best practices and tutorials on microservices architecture patterns"
```

### Industry Analysis
```
"Look up recent regulatory changes affecting financial technology companies"
```

### Product Research
```
"Find reviews and comparisons of enterprise messaging platforms"
```

## Configuration File Structure

The plugin uses a `config.yaml` file that contains:

```yaml
plugin:
  name: tavily
  version: 0.1.0
  description: "AI-powered web search using Tavily's intelligent search API"
  author: "Jamieson Walker <jamieson.walker@solace.com>"

sam_agent:
  # Complete SAM agent configuration
  # Tool definitions for Tavily API integration
  # System prompts and behavior configuration
```

## Advanced Features

### Query Optimization
- The plugin automatically optimizes search queries for better results
- Supports complex search operators and filters
- Handles multi-part queries and research topics

### Result Processing
- Intelligent result filtering based on relevance and quality
- Automatic duplicate detection and removal
- Content summarization for large result sets

### Search Modes
- **Quick Search**: Fast results for simple queries
- **Deep Research**: Comprehensive analysis for complex topics
- **Real-time Monitoring**: Continuous search for trending topics

## Best Practices

### 🎯 Query Formulation
- Use specific, descriptive queries for better results
- Include relevant context and timeframes when applicable
- Combine multiple related searches for comprehensive research

### 📊 Result Analysis
- Review result relevance scores and metadata
- Cross-reference findings from multiple searches
- Validate information from authoritative sources

### ⚡ Performance
- Use batch queries for related research topics
- Implement proper caching for repeated searches
- Monitor API usage and rate limits

### 🔒 Usage Guidelines
- Respect Tavily's terms of service and usage policies
- Be mindful of search volume limits
- Use appropriate search filters to reduce noise

## Troubleshooting

### Common Issues

**Plugin not found**: Ensure the plugin is properly installed in your SAM plugin directory.

**Authentication errors**: Verify your Tavily API key is correctly set in environment variables.

**No results returned**: Check your query formulation and try broader or alternative search terms.

**Rate limiting**: Monitor your API usage and consider upgrading your Tavily plan if needed.

### Getting Help

- Review the plugin's README.md file for detailed setup instructions
- Check the [Tavily documentation](https://docs.tavily.com/) for API-specific guidance
- Visit the [Solace Community](https://solace.community/) for plugin support and discussions

## Use Cases and Applications

### 📈 Business Intelligence
- Market research and competitive analysis
- Industry trend monitoring
- Customer sentiment analysis
- Regulatory compliance tracking

### 🔬 Research and Development
- Technical documentation discovery
- Academic paper and publication searches
- Patent and innovation research
- Best practices and methodology research

### 📰 Content and Marketing
- Content research and idea generation
- Trend analysis for content planning
- Competitor content analysis
- Industry news monitoring

### 🎯 Decision Support
- Due diligence research
- Vendor and partner evaluation
- Risk assessment and monitoring
- Strategic planning support

## Next Steps

After setting up the Tavily plugin:

1. **Explore Search Capabilities**: Experiment with different types of queries and search modes
2. **Integrate with Other Agents**: Combine Tavily search with data analysis and processing agents
3. **Monitor Usage**: Track your API usage and search result quality
4. **Scale Research Workflows**: Build automated research and monitoring processes

## Related Resources

- [Solace Agent Mesh Documentation](https://solacelabs.github.io/solace-agent-mesh/)
- [MCP Integration Guide](https://solacelabs.github.io/solace-agent-mesh/docs/documentation/tutorials/mcp-integration/)
- [Tavily Search API](https://www.tavily.com/)
- [Community Plugin Repository](https://github.com/solacecommunity/solace-agent-mesh-plugins)
