
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from typing import Dict, Any, List
import uvicorn
from .schemas import ListToolsRequest, CallToolRequest, FetchArgs
from .fetch import fetch_url, DEFAULT_USER_AGENT_AUTONOMOUS

app = FastAPI(title="MCP Fetch")

# Store active connections
connections: Dict[str, asyncio.Queue] = {}

async def event_generator(request: Request, queue: asyncio.Queue):
    try:
        while True:
            if await request.is_disconnected():
                break
            data = await queue.get()
            yield data
    finally:
        # Cleanup on disconnect
        for session_id, q in connections.items():
            if q == queue:
                del connections[session_id]
                break

@app.get("/sse")
async def sse(request: Request):
    queue = asyncio.Queue()
    session_id = str(len(connections))
    connections[session_id] = queue
    
    return EventSourceResponse(
        event_generator(request, queue),
        headers={
            "X-Session-ID": session_id
        }
    )

@app.post("/message")
async def message(request: Request):
    session_id = request.query_params.get("sessionId")
    if not session_id or session_id not in connections:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    
    data = await request.json()
    queue = connections[session_id]
    
    if isinstance(data, dict):
        if data.get("method") == "tools/list":
            response = handle_list_tools(ListToolsRequest(**data))
        elif data.get("method") == "tools/call":
            response = await handle_tool_call(CallToolRequest(**data))
        else:
            response = {"error": "Unknown method"}
        
        await queue.put({"data": response})
    
    return JSONResponse({"status": "ok"})

def handle_list_tools(request: ListToolsRequest) -> Dict[str, List[Dict[str, Any]]]:
    return {
        "tools": [
            {
                "name": "fetch",
                "description": "Retrieves URLs from the Internet and extracts their content as markdown. "
                             "If images are found, they are merged vertically (max 6 images per group, "
                             "max height 8000px, max size 30MB per group) and copied to the clipboard "
                             "of the user's host machine. You will need to paste (Cmd+V) to insert the images.",
                "inputSchema": FetchArgs.model_json_schema()
            }
        ]
    }

async def handle_tool_call(request: CallToolRequest) -> Dict[str, Any]:
    try:
        if request.params.name != "fetch":
            raise ValueError(f"Unknown tool: {request.params.name}")

        args = FetchArgs(**request.params.arguments or {})
        result = await fetch_url(
            str(args.url),
            DEFAULT_USER_AGENT_AUTONOMOUS,
            args.raw
        )

        content = result.content
        if len(content) > args.max_length:
            content = content[args.start_index:args.start_index + args.max_length]
            content += f"\n\n<e>Content truncated. Call the fetch tool with a start_index of {args.start_index + args.max_length} to get more content.</e>"

        images_section = ""
        if result.image_urls:
            images_section = "\n\nImages found in article:\n" + "\n".join(f"- {url}" for url in result.image_urls)

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"{result.prefix}Contents of {args.url}:\n{content}{images_section}"
                }
            ]
        }
    except Exception as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error: {str(e)}"
                }
            ],
            "isError": True
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3001)
