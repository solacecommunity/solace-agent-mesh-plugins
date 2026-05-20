# Web Agent Plugin

An agent plugin for Solace Agent Mesh that provides web request and search capabilities using DuckDuckGo.

## Description

This plugin enables agents to fetch content from web URLs and search the web using DuckDuckGo. It combines the built-in `web_request` tool with a custom `web_search` tool that supports multiple search types.

## Features

### 1. Web Requests (Built-in Tool)
- Make HTTP requests (GET, POST, etc.)
- Include custom headers or request body
- Returns HTML converted to Markdown, text content, or binary data
- Fetch content from any accessible web URL

### 2. Web Search (Custom Tool)

Search the web using DuckDuckGo with support for four search types:

**Text Search**
- Find web pages and documents
- Returns: title, URL, snippet
- Best for: General web searches, finding articles and documentation

**Image Search**
- Find images with metadata
- Returns: title, URL, image URL, thumbnail, dimensions, source
- Best for: Finding pictures, photos, illustrations

**Video Search**
- Find video content
- Returns: title, URL, description, duration, publisher, published date, thumbnail
- Best for: Finding video tutorials, clips, content

**News Search**
- Find recent news articles
- Returns: title, URL, snippet, date, source
- Best for: Current events, recent developments

### Search Features
- Configurable `max_results` parameter (default: 10)
- Results returned as structured data
- Automatically saved as JSON artifacts
- Comprehensive metadata for each result type

## Requirements

- Python >= 3.10
- `ddgs` package (DuckDuckGo search library)
- Solace Agent Mesh framework

## Installation

To add this plugin to your SAM project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=web-agent
```

This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.

Alternatively, you can install via the SAM Plugin Catalog:

1. Launch SAM plugin catalog: `sam plugin catalog`
2. Add this repository to your SAM instance if you have not done so already: `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the plugin using the install button in the GUI or with: `sam plugin add web-agent --plugin web-agent`

## Usage

Once the agent is running, you can interact with it through the SAM orchestrator using natural language prompts.

### Example Prompts

#### Text Search
- *"Search for information about Python asyncio"*
- *"Find articles about machine learning best practices"*
- *"Look up documentation for React hooks"*

#### Image Search
- *"Find images of butterflies"*
- *"Search for photos of mountain landscapes"*
- *"Show me pictures of vintage cars"*

#### Video Search
- *"Search for Python tutorial videos"*
- *"Find cooking videos for pasta recipes"*
- *"Look up exercise videos for beginners"*

#### News Search
- *"What's the latest news about artificial intelligence?"*
- *"Find recent news about climate change"*
- *"Search for today's technology news"*

#### Web Content Fetching
- *"Fetch the content from https://example.com"*
- *"Get the page content from this URL"*
- *"Download and show me the content of this webpage"*

## Tool Details

### web_search

Searches the web using DuckDuckGo.

**Parameters:**
- `query` (str, required): Search query string
- `search_type` (str, optional): Type of search - "text", "images", "videos", or "news" (default: "text")
- `max_results` (int, optional): Maximum number of results to return (default: 10)
- `save_as_artifact` (bool, optional): Whether to save results as JSON artifact (default: True)

**Returns:**
- `status`: "success" or "error"
- `message`: Human-readable message
- `search_type`: Type of search performed
- `query`: Original query string
- `results`: List of search results (structure varies by search type)
- `result_count`: Number of results returned
- `artifact_filename`: Name of saved artifact (if saved)
- `artifact_version`: Version of saved artifact (if saved)

**Result Structures:**

*Text Search Result:*
```json
{
  "title": "Page title",
  "url": "https://example.com",
  "snippet": "Description or excerpt"
}
```

*Image Search Result:*
```json
{
  "title": "Image title",
  "url": "https://example.com/page",
  "image_url": "https://example.com/image.jpg",
  "thumbnail": "https://example.com/thumb.jpg",
  "width": 1920,
  "height": 1080,
  "source": "example.com"
}
```

*Video Search Result:*
```json
{
  "title": "Video title",
  "url": "https://example.com/video",
  "description": "Video description",
  "duration": "10:30",
  "publisher": "Publisher Name",
  "published": "2024-01-01",
  "thumbnail": "https://example.com/thumb.jpg"
}
```

*News Search Result:*
```json
{
  "title": "Article title",
  "url": "https://news.example.com/article",
  "snippet": "Article excerpt",
  "date": "2024-01-01T12:00:00",
  "source": "News Source"
}
```

### web_request (Built-in)

Fetches content from web URLs. See SAM documentation for details.

## Artifact Output

When `save_as_artifact=True` (default), search results are saved as JSON files with the naming pattern:
```
search_{search_type}_{sanitized_query}_{timestamp}.json
```

Example: `search_text_python_asyncio_20240101_120000.json`

The JSON artifact contains:
```json
{
  "query": "search query",
  "search_type": "text",
  "result_count": 10,
  "timestamp": "2024-01-01T12:00:00Z",
  "results": [...]
}
```

## Development

### Debug Mode

For rapid development without rebuilding:

```bash
cd web-agent/src
sam run ../config.yaml
```

Changes to `tools.py` will be reflected immediately.

### Testing the Search Tool

You can test the search functionality independently:

```python
import asyncio
from web_agent.tools import web_search

# Mock tool context (for testing without SAM)
async def test_search():
    result = await web_search(
        query="Python programming",
        search_type="text",
        max_results=5,
        save_as_artifact=False,  # Skip artifact saving in tests
        tool_context=None
    )
    print(result)

asyncio.run(test_search())
```

## Architecture

The plugin follows the function-based tool pattern:
- `web_search` is an async function in `src/web_agent/tools.py`
- Uses the `ddgs` library for DuckDuckGo search
- Integrates with SAM artifact service for result storage
- Results are returned as structured data and optionally saved as JSON
- All search operations run in thread pool (ddgs is synchronous)

## Dependencies

- **ddgs**: DuckDuckGo search library (renamed from duckduckgo-search)
  - Provides text, image, video, and news search
  - No API key required
  - Privacy-focused search engine

## License

See project license.

## Author

Greg Meldrum <greg.meldrum@solace.com>
