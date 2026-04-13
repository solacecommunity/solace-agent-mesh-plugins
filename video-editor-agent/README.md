# Video Editor Agent SAM Plugin

A Solace Agent Mesh plugin that provides video editing capabilities using FFmpeg.

---

**Plugin Type:** `Custom Code Agent`

> **Note:** This is a community-contributed plugin for [Solace Agent Mesh (SAM)](https://solacelabs.github.io/solace-agent-mesh/) and is not officially supported by Solace. For community support, please open an issue in this repository.

---

## Overview

The Video Editor agent enables agents to perform video manipulation using FFmpeg. It provides tools for trimming, concatenating, format conversion, adding audio, applying filters, and extracting frames. This plugin handles complex video processing tasks through a simple tool interface.

## Features

This agent provides the following capabilities:

- **Video Trimming**: Cut videos to specific start and end times
- **Video Concatenation**: Join multiple videos together
- **Format Conversion**: Convert between video formats (MP4, AVI, MOV, WebM, etc.)
- **Audio Addition**: Add or replace audio tracks
- **Video Filters**: Apply effects and transformations
- **Frame Extraction**: Extract individual frames as images
- **Comprehensive Support**: Handles all FFmpeg-compatible formats

## Requirements

- Python >= 3.10
- **FFmpeg installed on the system**
- Solace Agent Mesh framework

### Installing FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

## Configuration

This plugin does not require any environment variables or API keys. FFmpeg must be installed and accessible from the command line.

### Configuration File (`config.yaml`)

The `config.yaml` in this plugin serves as a template. When you use `sam plugin add <component_name> --plugin video-editor-agent`, the following placeholders in the YAML structure will be replaced with variations of `<component_name>`:
- `__COMPONENT_UPPER_SNAKE_CASE_NAME__`
- `__COMPONENT_KEBAB_CASE_NAME__`
- `__COMPONENT_PASCAL_CASE_NAME__`

Customize the `config.yaml` in this plugin directory to define the base configuration for components created from it.

## Installation

To add this plugin to your SAM project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=video-editor-agent
```

This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.

Alternatively, you can install via the SAM Plugin Catalog:

1. Launch SAM plugin catalog: `sam plugin catalog`
2. Add this repository to your SAM instance if you have not done so already: `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the plugin using the install button in the GUI or with: `sam plugin add video-editor-agent --plugin video-editor-agent`

## Usage

Once the agent is running, you can interact with it through the SAM orchestrator using natural language prompts.

### Example Prompts

#### Video Trimming
- *"Trim video.mp4 from 00:30 to 01:45"*
- *"Cut the first 10 seconds from this video"*
- *"Extract the segment from 2:00 to 5:30 from the video"*

#### Video Concatenation
- *"Join clip1.mp4 and clip2.mp4 into one video"*
- *"Concatenate these three videos in order"*
- *"Merge all these video clips together"*

#### Format Conversion
- *"Convert video.avi to MP4 format"*
- *"Change this MOV file to WebM"*
- *"Re-encode this video as H.264 MP4"*

#### Audio Operations
- *"Add background_music.mp3 to this video"*
- *"Replace the audio track in this video"*
- *"Remove audio from this video"*

#### Filters and Effects
- *"Apply a blur filter to this video"*
- *"Rotate this video 90 degrees clockwise"*
- *"Speed up this video to 2x"*

#### Frame Extraction
- *"Extract frame at 1:30 from this video"*
- *"Get a thumbnail from the 5 second mark"*
- *"Save frames every 10 seconds from this video"*

### Tools Available

The agent includes tools for video editing and manipulation using FFmpeg for all operations.

## Limitations

- **FFmpeg Dependency**: Requires FFmpeg to be installed on the system
- **Processing Time**: Video operations can be time-intensive for large files
- **Memory Usage**: Large videos may require significant memory
- **Format Support**: Limited to FFmpeg-compatible formats

## Error Handling

The agent includes robust error handling:

- **FFmpeg Validation**: Checks FFmpeg availability before operations
- **File Validation**: Validates video file format and accessibility
- **Operation Errors**: Provides clear error messages for processing failures

---

## Original Author

Created by Greg Meldrum <greg.meldrum@solace.com>

## Contributing

To contribute to this plugin review [Contributing](/CONTRIBUTING.md)

---

## License

See project license.