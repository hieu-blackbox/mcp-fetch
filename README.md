# MCP Fetch (Python)

[![smithery badge](https://smithery.ai/badge/@kazuph/mcp-fetch)](https://smithery.ai/server/@kazuph/mcp-fetch)

Model Context Protocol server for fetching web content and processing images. This allows Claude Desktop (or any MCP client) to fetch web content and handle images appropriately.

**Note: This is a Python conversion of the original TypeScript/Node.js version.**

## Quick Start (For Users)

To use this tool with Claude Desktop, add the following to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "tools": {
    "fetch": {
      "command": "python3",
      "args": ["/path/to/mcp-fetch/main.py"]
    }
  }
}
```

### Required Setup

1. **Python Requirements**: Python 3.8+ is required
2. **Install Dependencies**: Run `pip install -r requirements.txt` in the project directory
3. **Enable Accessibility for Claude**:
   - Open System Settings
   - Go to Privacy & Security > Accessibility
   - Click the "+" button
   - Add Claude from your Applications folder
   - Turn ON the toggle for Claude

This accessibility setting is required for automated clipboard operations (Cmd+V) to work properly.

## For Developers

The following sections are for those who want to develop or modify the tool.

## Prerequisites

- Python 3.8+
- macOS (for clipboard operations)
- Claude Desktop (install from https://claude.ai/desktop)

## Installation

### Manual Installation
```bash
git clone https://github.com/kazuph/mcp-fetch.git
cd mcp-fetch
pip install -r requirements.txt
```

### Development Installation
```bash
git clone https://github.com/kazuph/mcp-fetch.git
cd mcp-fetch
pip install -e .
```

## Image Processing Specifications

When processing images from web content, the following limits are applied:

- Maximum 6 images per group
- Maximum height of 8000 pixels per group
- Maximum size of 30MB per group

If content exceeds these limits, images will be automatically split into multiple groups, and you'll need to paste (Cmd+V) multiple times.

## Configuration

1. Make sure Claude Desktop is installed and running.

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Modify your Claude Desktop config located at:
`~/Library/Application Support/Claude/claude_desktop_config.json`

You can easily find this through the Claude Desktop menu:
1. Open Claude Desktop
2. Click Claude on the Mac menu bar
3. Click "Settings"
4. Click "Developer"

Add the following to your MCP client's configuration:

```json
{
  "tools": {
    "fetch": {
      "command": "python3",
      "args": ["/path/to/mcp-fetch/main.py"]
    }
  }
}
```

## Running the Server

### Direct execution:
```bash
python3 main.py
```

### Using uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 3001
```

## Available Tools

- `fetch`: Retrieves URLs from the Internet and extracts their content as markdown. Images are automatically processed and prepared for clipboard operations.

## Python Dependencies

- **mcp**: Model Context Protocol SDK for Python
- **httpx**: Modern HTTP client for async requests
- **beautifulsoup4**: HTML parsing and manipulation
- **readability**: Content extraction from HTML
- **markdownify**: HTML to Markdown conversion
- **Pillow**: Image processing
- **fastapi**: Modern web framework for APIs
- **pydantic**: Data validation using Python type hints

## Notes

- This tool is designed for macOS only due to its dependency on macOS-specific clipboard operations.
- Images are processed using Pillow for optimal performance and quality.
- When multiple images are found, they are merged vertically with consideration for size limits.
- Animated GIFs are automatically handled by extracting their first frame.
- The server runs on FastAPI with SSE (Server-Sent Events) for MCP communication.

## Differences from TypeScript Version

- Uses Python's `asyncio` instead of Node.js async/await
- FastAPI instead of Express.js
- Pillow instead of Sharp for image processing
- httpx instead of node-fetch for HTTP requests
- Pydantic instead of Zod for data validation
- BeautifulSoup4 + readability instead of jsdom + @mozilla/readability
