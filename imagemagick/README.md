# ImageMagick Agent Plugin

An agent plugin for Solace Agent Mesh that provides image editing capabilities using ImageMagick.

## Description

This plugin enables agents to perform common image manipulation tasks using the powerful ImageMagick command-line tools. It assumes ImageMagick is installed on the system and accessible via the `convert` command.

## Features

### Image Operations

1. **Get Image Info** - Retrieve detailed image metadata
   - Dimensions (width x height)
   - Format (JPEG, PNG, GIF, etc.)
   - File size
   - Color space (RGB, sRGB, CMYK, etc.)
   - Bit depth
   - Compression type
   - Quality (for JPEG)

2. **Crop Image** - Crop images to specific dimensions and positions
   - Specify width, height, and x/y offsets
   - Automatic output naming with "_cropped" suffix

3. **Resize Image** - Resize images with flexible options
   - Resize by percentage (e.g., 50%)
   - Resize to specific width and/or height
   - Option to maintain or ignore aspect ratio

4. **Convert Image Format** - Convert between image formats
   - Supported formats: JPEG, PNG, GIF, WebP, BMP
   - Optional quality parameter for JPEG output

5. **Add Text Overlay** - Add text annotations to images
   - Configurable text position (north, south, east, west, center, etc.)
   - Customizable font size and color
   - Optional background color for text

## Requirements

- Python >= 3.10
- ImageMagick installed on the system (command-line `convert` tool must be available)
- Solace Agent Mesh framework

### Installing ImageMagick

**macOS:**
```bash
brew install imagemagick
```

**Ubuntu/Debian:**
```bash
sudo apt-get install imagemagick
```

**Windows:**
Download from https://imagemagick.org/script/download.php

## Installation

To add this plugin to your SAM project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=imagemagick
```

This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.

Alternatively, you can install via the SAM Plugin Catalog:

1. Launch SAM plugin catalog: `sam plugin catalog`
2. Add this repository to your SAM instance if you have not done so already: `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the plugin using the install button in the GUI or with: `sam plugin add imagemagick --plugin imagemagick`

## Usage

Once the agent is running, you can interact with it through the SAM orchestrator using natural language prompts.

### Example Prompts

#### Cropping
- *"Crop photo.jpg to 800x600 pixels starting at position 100,50"*
- *"Crop this image to a square 500x500"*
- *"Cut out the center 1000x1000 pixels from this image"*

#### Resizing
- *"Resize banner.png to 50% of its original size"*
- *"Make this image 1920 pixels wide"*
- *"Scale this photo down to 800x600"*

#### Format Conversion
- *"Convert image.png to JPEG with 90% quality"*
- *"Change this image to WebP format"*
- *"Convert this JPEG to PNG"*

#### Text Overlay
- *"Add Copyright 2024 text at the bottom of photo.jpg in white"*
- *"Put a watermark saying My Company in the center"*
- *"Add the text For Sale in red at the top of this image"*

#### Image Information
- *"What are the dimensions of photo.jpg?"*
- *"Get the file size and format of this image"*
- *"Show me the metadata for this picture"*

## Tool Details

### get_image_info

Retrieves detailed metadata about an image.

**Parameters:**
- `image_filename` (str): Input image with optional version

**Returns:**
- `format`: Image format (JPEG, PNG, GIF, etc.)
- `dimensions`: Object with `width` and `height` in pixels
- `file_size`: Human-readable file size (e.g., "245KB")
- `file_size_bytes`: Exact file size in bytes
- `colorspace`: Color space (sRGB, RGB, CMYK, etc.)
- `bit_depth`: Bits per pixel (optional)
- `compression`: Compression type
- `quality`: JPEG quality 0-100 (optional, JPEG only)

**Example Return:**
```json
{
  "status": "success",
  "message": "Image information retrieved successfully",
  "filename": "photo.jpg",
  "version": 1,
  "format": "JPEG",
  "dimensions": {"width": 1920, "height": 1080},
  "file_size": "245KB",
  "file_size_bytes": 251904,
  "colorspace": "sRGB",
  "bit_depth": 8,
  "compression": "JPEG",
  "quality": 85
}
```

### crop_image

Crops an image to specified dimensions.

**Parameters:**
- `image_filename` (str): Input image with optional version
- `width` (int): Crop width in pixels
- `height` (int): Crop height in pixels
- `x_offset` (int, optional): X position, default 0
- `y_offset` (int, optional): Y position, default 0
- `output_filename` (str, optional): Custom output name

### resize_image

Resizes an image.

**Parameters:**
- `image_filename` (str): Input image with optional version
- `width` (int, optional): Target width in pixels
- `height` (int, optional): Target height in pixels
- `percentage` (int, optional): Resize percentage
- `maintain_aspect_ratio` (bool): Keep aspect ratio, default True
- `output_filename` (str, optional): Custom output name

### convert_image_format

Converts image between formats.

**Parameters:**
- `image_filename` (str): Input image with optional version
- `output_format` (str): Target format (jpg, png, gif, webp, bmp)
- `quality` (int, optional): JPEG quality 1-100
- `output_filename` (str, optional): Custom output name

### add_text_overlay

Adds text overlay to an image.

**Parameters:**
- `image_filename` (str): Input image with optional version
- `text` (str): Text to overlay
- `position` (str): Position - north, south, east, west, center, northeast, northwest, southeast, southwest
- `font_size` (int): Font size in points, default 32
- `font_color` (str): Color name or hex code, default "white"
- `background_color` (str, optional): Background color for text
- `output_filename` (str, optional): Custom output name

## Development

### Debug Mode

For rapid development without rebuilding:

```bash
cd imagemagick/src
sam run ../config.yaml
```

Changes to `tools.py` will be reflected immediately.

### Testing ImageMagick Availability

Verify ImageMagick is installed:
```bash
convert -version
```

You should see output showing the ImageMagick version and features.

## Architecture

The plugin follows the function-based tool pattern:
- Each tool is an async function in `src/imagemagick/tools.py`
- Tools interact with the SAM artifact service for file I/O
- ImageMagick operations are executed via subprocess calls to the `convert` command
- Temporary files are used for processing and cleaned up automatically

## License

See project license.

## Author

Greg Meldrum <greg.meldrum@solace.com>
