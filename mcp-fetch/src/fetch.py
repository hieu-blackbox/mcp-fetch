
import aiohttp
from bs4 import BeautifulSoup
from readability import Document
import markdown2
from typing import Union
from .schemas import ExtractedContent, Image, ContentResponse
from .images import add_images_to_clipboard

DEFAULT_USER_AGENT_AUTONOMOUS = "ModelContextProtocol/1.0 (Autonomous; +https://github.com/modelcontextprotocol/servers)"
DEFAULT_USER_AGENT_MANUAL = "ModelContextProtocol/1.0 (User-Specified; +https://github.com/modelcontextprotocol/servers)"

async def fetch_url(url: str, user_agent: str = DEFAULT_USER_AGENT_AUTONOMOUS, raw: bool = False) -> ContentResponse:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={"User-Agent": user_agent}) as response:
            if not response.ok:
                raise ValueError(f"Failed to fetch URL: {response.status}")
            
            content_type = response.headers.get("content-type", "").lower()
            text = await response.text()

            if raw or "text/html" not in content_type:
                return ContentResponse(
                    content=text,
                    prefix=f"Content type {content_type} cannot be simplified to markdown, but here is the raw content:\n"
                )

            result = extract_content_from_html(text, str(url))
            if isinstance(result, str):
                return ContentResponse(content=result)

            fetchedImages = await fetch_images(result.images)
            image_urls = [img.src for img in fetchedImages]

            try:
                if fetchedImages:
                    await add_images_to_clipboard(fetchedImages)
                    return ContentResponse(
                        content=result.markdown,
                        prefix=f"Found and processed {len(fetchedImages)} images. Images have been merged vertically (max 6 images per group) and copied to your clipboard. Please paste (Cmd+V) to combine with the retrieved content.\n",
                        image_urls=image_urls
                    )
            except Exception as err:
                return ContentResponse(
                    content=result.markdown,
                    prefix=f"Found {len(fetchedImages)} images but failed to copy them to the clipboard.\nError: {str(err)}\n",
                    image_urls=image_urls
                )

            return ContentResponse(
                content=result.markdown,
                prefix="",
                image_urls=image_urls
            )

def extract_content_from_html(html: str, url: str) -> Union[ExtractedContent, str]:
    try:
        # Use readability to extract main content
        doc = Document(html)
        article = doc.summary()
        
        if not article:
            return "<e>Page failed to be simplified from HTML</e>"

        # Parse article HTML to extract images
        soup = BeautifulSoup(article, 'html.parser')
        images = []
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            if src:
                images.append(Image(src=src, alt=alt))

        # Convert HTML to Markdown
        markdown = markdown2.markdown(article)
        
        return ExtractedContent(markdown=markdown, images=images)
    except Exception as e:
        return f"<e>Failed to extract content: {str(e)}</e>"

async def fetch_images(images: list[Image]) -> list[Image]:
    fetched_images = []
    async with aiohttp.ClientSession() as session:
        for img in images:
            try:
                async with session.get(img.src) as response:
                    if response.ok:
                        img.data = await response.read()
                        fetched_images.append(img)
            except Exception as e:
                print(f"Failed to fetch image {img.src}: {str(e)}")
                continue
    return fetched_images
