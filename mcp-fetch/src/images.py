
import os
import subprocess
from PIL import Image as PILImage
from io import BytesIO
from typing import List, Tuple
import tempfile
import shutil
from .schemas import Image

async def get_image_dimensions(image_data: bytes) -> Tuple[int, int, int]:
    with BytesIO(image_data) as bio:
        with PILImage.open(bio) as img:
            return img.width, img.height, len(image_data)

async def command_exists(cmd: str) -> bool:
    try:
        subprocess.run(['which', cmd], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False

async def add_images_to_clipboard(images: List[Image]) -> None:
    if not images:
        return

    # Check for required commands
    has_pbcopy = await command_exists('pbcopy')
    has_osascript = await command_exists('osascript')
    
    if not has_pbcopy:
        raise RuntimeError("'pbcopy' command not found. This tool works on macOS only by default.")
    if not has_osascript:
        raise RuntimeError("'osascript' command not found. Required to set clipboard with images.")

    MAX_HEIGHT = 8000
    MAX_SIZE_BYTES = 30 * 1024 * 1024  # 30MB
    MAX_IMAGES_PER_GROUP = 6

    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix='mcp-fetch-images-')
    try:
        image_groups = []
        current_group = []
        current_height = 0
        current_size = 0

        # Group images
        for img in images:
            if not img.data:
                continue

            width, height, size = await get_image_dimensions(img.data)
            
            # Start new group if current one is full
            if (len(current_group) >= MAX_IMAGES_PER_GROUP or 
                current_height + height > MAX_HEIGHT or 
                current_size + size > MAX_SIZE_BYTES):
                if current_group:
                    image_groups.append(current_group)
                current_group = []
                current_height = 0
                current_size = 0

            current_group.append((BytesIO(img.data), height))
            current_height += height
            current_size += size

        if current_group:
            image_groups.append(current_group)

        # Process each group
        for group_idx, group in enumerate(image_groups):
            # Create vertical stack of images
            total_height = sum(h for _, h in group)
            max_width = max(PILImage.open(img).width for img, _ in group)
            
            combined = PILImage.new('RGB', (max_width, total_height), 'white')
            y_offset = 0
            
            for img_data, height in group:
                img = PILImage.open(img_data)
                if img.mode == 'RGBA':
                    # Convert RGBA to RGB with white background
                    background = PILImage.new('RGB', img.size, 'white')
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                combined.paste(img, (0, y_offset))
                y_offset += height

            # Save combined image
            output_path = os.path.join(temp_dir, f'group_{group_idx}.png')
            combined.save(output_path, 'PNG')
            
            # Copy to clipboard using osascript
            applescript = f'''
            set theFile to POSIX file "{output_path}"
            set theImage to (read theFile as JPEG picture)
            set the clipboard to theImage
            '''
            subprocess.run(['osascript', '-e', applescript], check=True)

    finally:
        # Cleanup temporary directory
        shutil.rmtree(temp_dir)
