# Object Detection SAM Plugin

A Solace Agent Mesh plugin that provides YOLO-based object detection capabilities using the YOLOv12 model.

---

**Plugin Type:** `Custom Code Agent`

> **Note:** This is a community-contributed plugin for [Solace Agent Mesh (SAM)](https://solacelabs.github.io/solace-agent-mesh/) and is not officially supported by Solace. For community support, please open an issue in this repository.

---

## Overview

The Object Detection agent enables agents to perform object recognition on images using the state-of-the-art YOLOv12 model. It processes image artifacts, identifies objects, and returns bounding boxes with confidence scores. The agent can filter detections by class or confidence threshold, making it ideal for computer vision pipelines requiring real-time object recognition.

## Features

This agent provides the following capabilities:

- **Object Detection**: Identify and locate objects in images using YOLOv12
- **Bounding Boxes**: Get precise object locations with coordinates
- **Confidence Scores**: Receive confidence levels for each detection
- **Class Filtering**: Filter detections by specific object classes
- **Threshold Control**: Set minimum confidence thresholds for detections
- **Image Artifact Support**: Process images from SAM's artifact system

## Configuration

This plugin does not require any environment variables or API keys.

### Configuration File (`config.yaml`)

The `config.yaml` in this plugin serves as a template. When you use `sam plugin add <component_name> --plugin object-detection`, the following placeholders in the YAML structure will be replaced with variations of `<component_name>`:
- `__COMPONENT_UPPER_SNAKE_CASE_NAME__`
- `__COMPONENT_KEBAB_CASE_NAME__`
- `__COMPONENT_PASCAL_CASE_NAME__`

Customize the `config.yaml` in this plugin directory to define the base configuration for components created from it.

## Installation

To add this plugin to your SAM project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=object-detection
```

This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.

Alternatively, you can install via the SAM Plugin Catalog:

1. Launch SAM plugin catalog: `sam plugin catalog`
2. Add this repository to your SAM instance if you have not done so already: `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the plugin using the install button in the GUI or with: `sam plugin add object-detection --plugin object-detection`

## Usage

Once the agent is running, you can interact with it through the SAM orchestrator using natural language prompts.

### Example Prompts

#### Object Counting
- *"Count the number of cars, trucks and buses in this image"*
- *"How many people are in this photo?"*

#### Object Detection
- *"What objects can you detect in this image?"*
- *"Find all the vehicles in this picture"*
- *"Detect all persons in this image"*

#### Specific Object Searches
- *"Are there any dogs in this image?"*
- *"Find all the chairs in this room"*
- *"Locate all stop signs in this photo"*

### Tools Available

The agent includes tools for object detection and analysis using the YOLOv12 model.

### Detectable Object Classes

The YOLOv12 model is trained on the COCO dataset and can detect the following object classes:

**Person**
- person

**Vehicles**
- bicycle, car, motorcycle, airplane, bus, train, truck, boat

**Outdoor**
- traffic light, fire hydrant, stop sign, parking meter, bench

**Animals**
- bird, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe

**Household / Indoor**
- backpack, umbrella, handbag, tie, suitcase, chair, couch, potted plant, bed, dining table, toilet, tv, laptop, mouse, remote, keyboard, cell phone, microwave, oven, toaster, sink, refrigerator, book, clock, vase, scissors, teddy bear, hair drier, toothbrush

## Limitations

- **Model Size**: YOLOv12 model requires significant memory (~40MB model file)
- **Processing Time**: Detection speed depends on image size and hardware
- **Object Classes**: Limited to YOLO's pre-trained object classes
- **Image Formats**: Supports standard image formats (JPEG, PNG, etc.)

## Error Handling

The agent includes robust error handling:

- **Image Loading**: Validates image format and accessibility
- **Model Loading**: Handles model initialization errors
- **Detection Errors**: Provides clear error messages for detection failures

---

## Original Author

Created by Greg Meldrum <greg.meldrum@solace.com>

## Contributing

To contribute to this plugin review [Contributing](/CONTRIBUTING.md)

---

## License

See project license.