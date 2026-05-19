# Local TTS SAM Plugin

A Solace Agent Mesh plugin that provides text-to-speech capabilities using Microsoft's VibeVoice framework.

---

**Plugin Type:** `Custom Code Agent`

> **Note:** This is a community-contributed plugin for [Solace Agent Mesh (SAM)](https://solacelabs.github.io/solace-agent-mesh/) and is not officially supported by Solace. For community support, please open an issue in this repository.

---

## Overview

The Local TTS agent enables SAM to convert text to natural-sounding speech using Microsoft's VibeVoice framework. All inference runs locally for maximum privacy, generating high-quality audio artifacts from text input with support for multiple voices.

## Features

This agent provides the following capabilities:

- **Local Inference**: Runs entirely on-device using VibeVoice
- **Privacy First**: No data sent to external services
- **Multiple Voices**: Choose from four high-quality voices
  - Carter (male voice)
  - Davis (male voice)
  - Emma (female voice)
  - Grace (female voice)
- **Audio Artifacts**: Generates audio files as SAM artifacts
- **Natural Speech**: High-quality, natural-sounding voice synthesis
- **Customizable**: Adjust voice selection per request

## Requirements

> **⚠️ Important**: This plugin requires `transformers==4.51.3`. It **cannot** be installed in the same environment as the Local MLX Vision plugin, which requires `transformers>=4.57.3`. These two plugins must be run in separate environments due to conflicting transformers library versions.

## Configuration

This plugin does not require any environment variables or API keys.

### Configuration File (`config.yaml`)

The `config.yaml` in this plugin serves as a template. When you use `sam plugin add <component_name> --plugin local-tts`, the following placeholders in the YAML structure will be replaced with variations of `<component_name>`:
- `__COMPONENT_UPPER_SNAKE_CASE_NAME__`
- `__COMPONENT_KEBAB_CASE_NAME__`
- `__COMPONENT_PASCAL_CASE_NAME__`

Customize the `config.yaml` in this plugin directory to define the base configuration for components created from it.

## Installation

### 1. Install the Hugging Face CLI (Recommended)

To pre-download the model and avoid long waits during first use:

```bash
pip install "huggingface-hub[cli]"
```

### 2. Pre-download the Model (Recommended)

Download the model before using the plugin to avoid timeouts:

```bash
huggingface-cli download microsoft/VibeVoice-Realtime-0.5B
```

This may take several minutes. Without pre-downloading, the model will load on first invocation, which may take a long time and could fail the task.

### 3. Install the Plugin

To add this plugin to your SAM project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=local-tts
```

This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.

Alternatively, you can install via the SAM Plugin Catalog:

1. Launch SAM plugin catalog: `sam plugin catalog`
2. Add this repository to your SAM instance if you have not done so already: `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the plugin using the install button in the GUI or with: `sam plugin add local-tts --plugin local-tts`

## Usage

Once the agent is running, you can interact with it through the SAM orchestrator using natural language prompts.

### Example Prompts

#### Basic Text-to-Speech
- *"Say hello there in the voice of a woman"*
- *"Convert this text to speech using Emma's voice"*
- *"Read this paragraph out loud"*

#### Voice Selection
- *"Say welcome to our service using Carter's voice"*
- *"Use Grace's voice to say good morning"*
- *"Generate audio of this announcement in Davis's voice"*

#### Content Generation
- *"Create an audio file saying the meeting starts at 3pm"*
- *"Generate speech for this script"*
- *"Make an audio announcement for this event"*

### Tools Available

The agent includes a text-to-speech tool that converts text to natural-sounding audio using VibeVoice models.

## Limitations

- **Model Size**: VibeVoice model requires significant storage
- **Processing Time**: Speech generation speed depends on text length and hardware
- **Voice Options**: Limited to four pre-trained voices
- **Languages**: Optimized for English language content

## Error Handling

The agent includes robust error handling:

- **Model Loading**: Handles model initialization errors
- **Text Processing**: Validates input text
- **Audio Generation**: Provides clear error messages for generation failures

---

## Original Author

Created by Greg Meldrum <greg.meldrum@solace.com>

## Contributing

To contribute to this plugin review [Contributing](/CONTRIBUTING.md)

---

## License

See project license.