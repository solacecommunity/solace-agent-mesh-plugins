# Local MLX Vision - SAM Agent Plugin

A Solace Agent Mesh (SAM) plugin that provides local vision language model capabilities using MLX on Apple Silicon. This agent can analyze images, perform OCR, extract structured data, and answer questions about visual content - all running locally for maximum privacy.

## Overview

This plugin enables SAM agents to process images using the Qwen3-VL-2B-Instruct-4bit model via the MLX framework. All inference runs locally on your Mac with Apple Silicon, ensuring fast performance and complete data privacy.

### Key Features

- **Local Inference**: Runs entirely on-device using Apple's MLX framework
- **Privacy First**: No data sent to external services
- **Multiple Input Modes**: Supports both SAM artifacts and direct file paths
- **Versatile Analysis**: OCR, object detection, image description, structured data extraction
- **Configurable**: Adjust temperature, max tokens, and system messages
- **Apple Silicon Optimized**: Leverages Metal acceleration for fast inference

## Requirements

### Platform Requirements

- **macOS** with **Apple Silicon** (M1, M2, M3, or later)
- Python 3.10 or higher
- Minimum 8GB RAM (16GB recommended)

> **⚠️ Important**: This plugin requires `transformers>=4.57.3`. It **cannot** be installed in the same environment as the Local TTS plugin, which requires `transformers==4.51.3`. These two plugins must be run in separate environments due to conflicting transformers library versions.

### Dependencies

The plugin automatically installs:
- `mlx` - Apple's ML framework
- `mlx-vlm` - Vision language model support
- `transformers` - Model loading and tokenization
- `pillow` - Image processing
- `numpy` - Numerical operations

## Installation

### 1. Install the Hugging Face CLI (Recommended)

To pre-download the model and avoid long waits during first use:

```bash
pip install "huggingface-hub[cli]"
```

### 2. Pre-download the Model (Recommended)

Download the model before using the plugin to avoid timeouts:

```bash
huggingface-cli download mlx-community/Qwen3-VL-2B-Instruct-4bit
```

This downloads ~2GB and may take several minutes. Without pre-downloading, the model will load on first invocation, which may take a long time and could fail the task.

### 3. Install the Plugin

To add this plugin to your SAM project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=local-mlx-vision
```

This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.

Alternatively, you can install via the SAM Plugin Catalog:

1. Launch SAM plugin catalog: `sam plugin catalog`
2. Add this repository to your SAM instance if you have not done so already: `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the plugin using the install button in the GUI or with: `sam plugin add local-mlx-vision --plugin local-mlx-vision`

## Usage

Once the agent is running, you can interact with it through the SAM orchestrator using natural language prompts.

### Example Prompts

#### OCR and Data Extraction
- *"OCR this receipt and extract all fields as JSON"*
- *"Extract the name, address, and phone number from this form"*
- *"Read all the text from this document image"*

#### Image Description
- *"What's happening in this image?"*

#### Structured Data Extraction
- *"Extract all fields from this invoice and format as JSON"*
- *"List all the items and prices from this menu"*
- *"What are the key details from this business card?"*

### Using the Tool Directly

The `analyze_image` tool accepts the following parameters:

- **prompt** (required): Your question or instruction for the model
- **image_path** (optional): Direct path to an image file
- **image_artifact** (optional): SAM artifact reference (format: `filename:version` or `filename`)
- **system_message** (optional): System prompt to guide model behavior
- **max_tokens** (default: 4000): Maximum response length
- **temperature** (default: 0.0): Sampling temperature (0.0 = deterministic)

**Note**: You must provide either `image_path` OR `image_artifact`.

## Configuration

### Agent Configuration

The agent is configured in `config.yaml`. Key sections:

```yaml
tools:
  - tool_type: python
    component_module: local_mlx_vision.tools
    function_name: analyze_image
    tool_config:
      model: "mlx-community/Qwen3-VL-2B-Instruct-4bit"
```

### Using a Different Model

To use a different mlx-vlm compatible model, update the `tool_config`:

```yaml
tool_config:
  model: "mlx-community/some-other-vlm-model"
```

Ensure the model is compatible with `mlx-vlm`.

## Technical Details

### How It Works

1. **Image Input**: The agent receives an image via artifact or file path
2. **Validation**: Platform is validated (macOS + Apple Silicon required)
3. **Processing**: Image is processed by the MLX vision model
4. **Inference**: Model generates a text response based on your prompt
5. **Response**: Text response is returned to the user

### Performance

- **First Run**: 15-30 seconds (model download + loading)
- **Subsequent Runs**: 10-60 seconds depending on image complexity
- **Model Size**: ~2GB disk space for Qwen3-VL-2B-Instruct-4bit
- **Memory Usage**: ~4-6GB during inference

### Artifact Handling

When using SAM artifacts:
1. Artifact is loaded from the artifact service
2. Saved to a temporary file
3. Processed by the vision model
4. Temporary file is cleaned up automatically

## Development

### Debug Mode

For rapid development without reinstalling:

```bash
cd local-mlx-vision/src
sam run ../config.yaml
```

Changes to `tools.py` take effect immediately.

### Testing

Run the standalone test:

```bash
cd local-mlx-vision/src
python -m local_mlx_vision.tools
```

This validates platform compatibility and tests the analyze_image function.

### Logging

The plugin uses Python's standard logging. Set log levels in `config.yaml`:

```yaml
log:
  stdout_log_level: INFO
  log_file_level: DEBUG
  log_file: vision-agent.log
```

## Troubleshooting

### "Platform validation failed"

**Cause**: Not running on macOS with Apple Silicon

**Solution**: This plugin requires a Mac with M1/M2/M3 chip. Consider using a cloud-based vision API plugin for other platforms.

### "mlx-vlm command failed"

**Cause**: MLX dependencies not installed correctly

**Solution**:
```bash
pip install --upgrade mlx mlx-vlm
```

### Model Download Fails

**Cause**: Network issues or insufficient disk space

**Solution**:
- Ensure stable internet connection
- Free up at least 3GB disk space
- Try downloading manually:
  ```bash
  python -m mlx_vlm.download --model mlx-community/Qwen3-VL-2B-Instruct-4bit
  ```

### Slow Performance

**Cause**: Insufficient memory or thermal throttling

**Solution**:
- Close other applications
- Ensure adequate cooling
- Consider using a smaller max_tokens value

### Artifact Loading Fails

**Cause**: Missing context or artifact service not configured

**Solution**: Verify `artifact_service` is configured in `config.yaml`:
```yaml
artifact_service:
  type: "filesystem"
  base_path: "/tmp/samv2"
  artifact_scope: namespace
```

## Examples

### Example 1: Receipt OCR with JSON Output

```
Prompt: "OCR this receipt image and provide all fields in JSON format with keys: store_name, date, items (array), total_amount"

Image: receipt.jpg

Response:
{
  "store_name": "Joe's Market",
  "date": "2024-12-09",
  "items": [
    {"name": "Milk", "price": 3.99},
    {"name": "Bread", "price": 2.49},
    {"name": "Eggs", "price": 4.99}
  ],
  "total_amount": 11.47
}
```

### Example 2: Image Description

```
Prompt: "Describe this image in detail, including objects, people, setting, and activities"

Image: family_photo.jpg

Response: "The image shows a family of four at a beach during sunset. There are two adults and two children. They are standing near the water's edge with waves in the background. The children appear to be building a sandcastle. Everyone is smiling and wearing casual summer clothing..."
```

### Example 3: Form Field Extraction

```
Prompt: "Extract the following fields from this form: Name, Address, Phone, Email"

Image: application_form.png

Response:
Name: John Smith
Address: 123 Main Street, Anytown, CA 94000
Phone: (555) 123-4567
Email: john.smith@example.com
```

## Support

For issues and questions:
- Check the [SAM Documentation](https://solacelabs.github.io/solace-agent-mesh/)
- Review the plugin's `tools.py` for implementation details
- Ensure platform requirements are met

## Contributing

Contributions welcome! Consider adding:
- Support for additional MLX vision models
- Batch image processing
- Image preprocessing options
- Caching for repeated queries

## Changelog

### 0.1.0 (Initial Release)
- Local MLX vision model integration
- Support for Qwen3-VL-2B-Instruct-4bit
- Apple Silicon platform validation
- SAM artifact and file path input modes
- Comprehensive OCR and image analysis capabilities

## License

See project license.

## Author

Greg Meldrum <greg.meldrum@solace.com>
