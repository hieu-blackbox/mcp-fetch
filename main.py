#!/usr/bin/env python3

import asyncio
import base64
import io
import json
import os
import subprocess
import tempfile
from typing import Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from markdownify import markdownify as md
from PIL import Image
from pydantic import BaseModel, Field, HttpUrl
from readability import parse

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp import Tool

# Constants
DEFAULT_USER_AGENT_AUTONOMOUS = "ModelContextProtocol/1.0 (Autonomous; +https://github.com/modelcontextprotocol/servers)"
DEFAULT_USER_AGENT_MANUAL = "ModelContextProtocol/1.0 (User-Specified; +https://github.com/modelcontextprotocol/servers)"

# Pydantic models
class ImageData(BaseModel):
    src: str
    alt: str
    data: Optional[bytes] = None

class ExtractedContent(BaseModel):
    markdown: str
    images: List[ImageData]

class FetchArgs(BaseModel):
    url: HttpUrl
    max_length: int = Field(default=20000, gt=0, le=1000000)
    start_index: int = Field(default=0, ge=0)
    raw: bool = Field(default=False)

def sleep_ms(ms: int):
    """Sleep for specified milliseconds"""
    return asyncio.sleep(ms / 1000)

def extract_content_from_html(html: str, url: str) -> Union[ExtractedContent, str]:
    """Extract readable content from HTML using readability and convert to markdown"""
    try:
        article = parse(html, url)
        article_html = article.content
        
        if not article_html:
            return "<e>Page failed to be simplified from HTML</e>"
        
        # Extract images from the article content
        soup = BeautifulSoup(article_html, 'html.parser')
        img_elements = soup.find_all('img')
        
        images = []
        for img in img_elements:
            src = img.get('src', '')
            alt = img.get('alt', '')
            if src:
                # Convert relative URLs to absolute
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    parsed_url = urlparse(url)
                    src = f"{parsed_url.scheme}://{parsed_url.netloc}{src}"
                elif not src.startswith(('http://', 'https://')):
                    src = urljoin(url, src)
                images.append(ImageData(src=src, alt=alt))
        
        # Convert HTML to markdown
        markdown = md(article_html, heading_style="atx", code_block_style="fenced")
        
        return ExtractedContent(markdown=markdown, images=images)
    
    except Exception as e:
        return f"<e>Error extracting content: {str(e)}</e>"

async def fetch_images(images: List[ImageData]) -> List[ImageData]:
    """Fetch image data for all images"""
    fetched_images = []
    
    async with httpx.AsyncClient() as client:
        for img in images:
            try:
                response = await client.get(img.src, timeout=30.0)
                response.raise_for_status()
                
                image_buffer = response.content
                
                # Check if the image is a GIF and extract first frame if animated
                if img.src.lower().endswith('.gif'):
                    try:
                        pil_image = Image.open(io.BytesIO(image_buffer))
                        if hasattr(pil_image, 'n_frames') and pil_image.n_frames > 1:
                            # Extract first frame of animated GIF
                            pil_image.seek(0)
                            first_frame = io.BytesIO()
                            pil_image.save(first_frame, format='PNG')
                            image_buffer = first_frame.getvalue()
                    except Exception as e:
                        print(f"Warning: Failed to process GIF image {img.src}: {e}")
                
                fetched_images.append(ImageData(
                    src=img.src,
                    alt=img.alt,
                    data=image_buffer
                ))
                
            except Exception as e:
                print(f"Failed to fetch image {img.src}: {e}")
                continue
    
    return fetched_images

async def command_exists(cmd: str) -> bool:
    """Check if a command exists in the system"""
    try:
        result = await asyncio.create_subprocess_exec(
            'which', cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await result.communicate()
        return result.returncode == 0
    except:
        return False

async def get_image_dimensions(buffer: bytes) -> Dict[str, int]:
    """Get image dimensions and size"""
    try:
        pil_image = Image.open(io.BytesIO(buffer))
        return {
            'width': pil_image.width,
            'height': pil_image.height,
            'size': len(buffer)
        }
    except:
        return {'width': 0, 'height': 0, 'size': len(buffer)}

async def add_images_to_clipboard(images: List[ImageData]) -> None:
    """Add images to clipboard (macOS only)"""
    if not images:
        return
    
    # Check for required commands
    if not await command_exists("pbcopy"):
        raise Exception("'pbcopy' command not found. This tool works on macOS only by default.")
    
    if not await command_exists("osascript"):
        raise Exception("'osascript' command not found. Required to set clipboard with images.")
    
    MAX_HEIGHT = 8000
    MAX_SIZE_BYTES = 30 * 1024 * 1024  # 30MB
    MAX_IMAGES_PER_GROUP = 6
    
    # Create temporary directory
    temp_dir = "/tmp/mcp-fetch-images"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Process images in groups
        groups = []
        current_group = []
        current_height = 0
        current_size = 0
        
        for img in images:
            if not img.data:
                continue
                
            dims = await get_image_dimensions(img.data)
            
            # Check if adding this image would exceed limits
            if (len(current_group) >= MAX_IMAGES_PER_GROUP or
                current_height + dims['height'] > MAX_HEIGHT or
                current_size + dims['size'] > MAX_SIZE_BYTES):
                
                if current_group:
                    groups.append(current_group)
                    current_group = []
                    current_height = 0
                    current_size = 0
            
            current_group.append(img)
            current_height += dims['height']
            current_size += dims['size']
        
        if current_group:
            groups.append(current_group)
        
        # Process each group
        for i, group in enumerate(groups):
            if len(group) == 1:
                # Single image - save directly
                img = group[0]
                temp_path = f"{temp_dir}/image_{i}.png"
                
                try:
                    pil_image = Image.open(io.BytesIO(img.data))
                    pil_image.save(temp_path, 'PNG')
                except:
                    # If PIL fails, save raw data
                    with open(temp_path, 'wb') as f:
                        f.write(img.data)
            else:
                # Multiple images - merge vertically
                pil_images = []
                total_width = 0
                total_height = 0
                
                for img in group:
                    try:
                        pil_img = Image.open(io.BytesIO(img.data))
                        pil_images.append(pil_img)
                        total_width = max(total_width, pil_img.width)
                        total_height += pil_img.height
                    except:
                        continue
                
                if pil_images:
                    # Create merged image
                    merged = Image.new('RGB', (total_width, total_height), 'white')
                    y_offset = 0
                    
                    for pil_img in pil_images:
                        if pil_img.mode != 'RGB':
                            pil_img = pil_img.convert('RGB')
                        merged.paste(pil_img, (0, y_offset))
                        y_offset += pil_img.height
                    
                    temp_path = f"{temp_dir}/merged_{i}.png"
                    merged.save(temp_path, 'PNG')
            
            # Copy to clipboard using osascript
            applescript = f"""set the clipboard to (read (POSIX file "{temp_path}") as JPEG picture)"""
            
            process = await asyncio.create_subprocess_exec(
                'osascript', '-e', applescript,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if len(groups) > 1:
                print(f"Group {i+1}/{len(groups)} copied to clipboard. Please paste (Cmd+V) to use.")
                if i < len(groups) - 1:
                    await asyncio.sleep(1)  # Brief pause between groups
    
    finally:
        # Cleanup temp files
        try:
            subprocess.run(['rm', '-rf', temp_dir], check=False)
        except:
            pass

async def fetch_url(url: str, user_agent: str, raw: bool = False) -> Dict[str, Union[str, List[str]]]:
    """Fetch and process URL content"""
    headers = {'User-Agent': user_agent}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            
            if raw or 'text/html' not in content_type:
                return {
                    'content': response.text,
                    'prefix': f'Content type {content_type} cannot be simplified to markdown, but here is the raw content:\n'
                }
            
            # Process HTML content
            result = extract_content_from_html(response.text, url)
            
            if isinstance(result, str):
                return {'content': result, 'prefix': ''}
            
            # Fetch images
            fetched_images = await fetch_images(result.images)
            image_urls = [img.src for img in fetched_images]
            
            if fetched_images:
                try:
                    await add_images_to_clipboard(fetched_images)
                    return {
                        'content': result.markdown,
                        'prefix': f'Found and processed {len(fetched_images)} images. Images have been merged vertically (max 6 images per group) and copied to your clipboard. Please paste (Cmd+V) to combine with the retrieved content.\n',
                        'image_urls': image_urls
                    }
                except Exception as err:
                    return {
                        'content': result.markdown,
                        'prefix': f'Found {len(fetched_images)} images but failed to copy them to the clipboard.\nError: {str(err)}\n',
                        'image_urls': image_urls
                    }
            
            return {
                'content': result.markdown,
                'prefix': '',
                'image_urls': image_urls
            }
            
        except Exception as e:
            raise Exception(f"Failed to fetch URL: {str(e)}")

# Create MCP Server
server = Server("mcp-fetch")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="fetch",
            description="Retrieves URLs from the Internet and extracts their content as markdown. If images are found, they are merged vertically (max 6 images per group, max height 8000px, max size 30MB per group) and copied to the clipboard of the user's host machine. You will need to paste (Cmd+V) to insert the images.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "format": "uri"},
                    "max_length": {"type": "integer", "minimum": 1, "maximum": 1000000, "default": 20000},
                    "start_index": {"type": "integer", "minimum": 0, "default": 0},
                    "raw": {"type": "boolean", "default": False}
                },
                "required": ["url"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[dict]:
    """Handle tool calls"""
    try:
        if name != "fetch":
            raise Exception(f"Unknown tool: {name}")
        
        # Validate arguments
        try:
            args = FetchArgs(**arguments)
        except Exception as e:
            raise Exception(f"Invalid arguments: {str(e)}")
        
        # Fetch URL
        result = await fetch_url(
            str(args.url),
            DEFAULT_USER_AGENT_AUTONOMOUS,
            args.raw
        )
        
        content = result['content']
        prefix = result.get('prefix', '')
        image_urls = result.get('image_urls', [])
        
        # Apply length limits
        if len(content) > args.max_length:
            content = content[args.start_index:args.start_index + args.max_length]
            content += f"\n\n<e>Content truncated. Call the fetch tool with a start_index of {args.start_index + args.max_length} to get more content.</e>"
        
        # Add images section
        images_section = ""
        if image_urls:
            images_section = "\n\nImages found in article:\n" + "\n".join(f"- {url}" for url in image_urls)
        
        return [
            {
                "type": "text",
                "text": f"{prefix}Contents of {args.url}:\n{content}{images_section}"
            }
        ]
        
    except Exception as error:
        return [
            {
                "type": "text",
                "text": f"Error: {str(error)}"
            }
        ]

async def main():
    """Main function to run the MCP server"""
    # For stdio transport (standard MCP usage)
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-fetch",
                server_version="0.8.11",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
