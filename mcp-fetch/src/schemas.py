
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any, List, Literal

class FetchArgs(BaseModel):
    url: HttpUrl
    max_length: int = Field(default=20000, gt=0, le=1000000)
    start_index: int = Field(default=0, ge=0)
    raw: bool = False

class Image(BaseModel):
    src: str
    alt: str
    data: Optional[bytes] = None

class ExtractedContent(BaseModel):
    markdown: str
    images: List[Image]

class ListToolsRequest(BaseModel):
    method: Literal["tools/list"]

class ToolCallParams(BaseModel):
    name: str
    arguments: Optional[Dict[str, Any]] = None

class CallToolRequest(BaseModel):
    method: Literal["tools/call"]
    params: ToolCallParams

class ContentResponse(BaseModel):
    content: str
    prefix: str = ""
    image_urls: Optional[List[str]] = None

class ToolResponse(BaseModel):
    content: List[Dict[str, str]]
    is_error: bool = False
