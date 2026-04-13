[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-v2.0%20adopted-ff69b4.svg)](CODE_OF_CONDUCT.md)

# Solace Agent Mesh Community Plugins

## Overview
This repository contains a collection of plugins for [Solace Agent Mesh (SAM)](https://github.com/SolaceLabs/solace-agent-mesh). These plugins extend the functionality of SAM by providing additional capabilities and integrations. These plugins are built by the community and are not officially supported by Solace. 
⭐️ Please leave a star on the [Solace Agent Mesh (SAM)](https://github.com/SolaceLabs/solace-agent-mesh) repo while you are there. 

## Available Plugins
*This section will be updated as plugins are added to the repository.*

| Name                       | Website                                         | Description                                   |
|----------------------------|-------------------------------------------------|-----------------------------------------------|
| [Tavily MCP Agent Plugin](./tavily/)    | [Tavily](https://www.tavily.com/)               | Web scraping tool                             |
| [BrightData MCP Agent Plugin](./bright-data/) | [Bright Data](https://brightdata.com/)          | Web scraping tool                             |
| [SendGrid Agent Plugin](./send-grid/)      | [SendGrid](https://sendgrid.com/)               | Email sending service                         |
| [Find My IP Agent Plugin](./find-my-ip/)    | IP Detection: [IPify](https://ipify.org/) Geolocation: [ipapi.co](https://ipapi.co/), [ip-api.com](http://ip-api.com/), [ipinfo.io](https://ipinfo.io/), [ipwhois.io](https://ipwhois.io/) | IP, Location & Connection/Security Information |
| [Zapier](./zapier)| [Zapier](https://zapier.com/) | Integration with Zapiers connectors as MCP servers |
| [Object Detection](./object-detection/) | [YOLO](https://docs.ultralytics.com/) | YOLO-based object detection with YOLOv12 model |
| [Local MLX Vision](./local-mlx-vision/) | [MLX](https://github.com/ml-explore/mlx) | Vision language model (QwenVL) on Apple Silicon using MLX framework |
| [Artifact Host Agent](./artifact-host-agent/) | - | Web server for hosting artifacts via HTTP |
| [ImageMagick Agent](./imagemagick/) | [ImageMagick](https://imagemagick.org/) | Image manipulation and processing |
| [Web Agent](./web-agent/) | [DuckDuckGo](https://duckduckgo.com/) | Web search and content fetching |
| [Local TTS](./local-tts/) | [VibeVoice](https://github.com/microsoft/VibeVoice) | Text-to-speech using Microsoft's VibeVoice |
| [Video Editor Agent](./video-editor-agent/) | [FFmpeg](https://ffmpeg.org/) | Video editing and manipulation using FFmpeg |



## Getting started quickly
1. Launch SAM plugin catalog from you CLI `sam plugin catalog` 
2. Add this repository to your SAM instance if you have not done so already.  `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the desired agent using the install button in the gui or with `sam plugin add <desired-agent> --plugin <desired-agent>`

## Documentation
This repository primarily houses Plugins for community created agents and gateways for Solace Agent Mesh.  Each plugin will serve a different purpose and have its own set of usage instructions and required configuration.  Please review the Readme.md in the directory for the plugins you wish to use. 

## Resources
This is not an officially supported Solace product.
Find more information about [Solace Agent mesh](https://github.com/SolaceLabs/solace-agent-mesh) in the open source project or on the [Solace Products page for SAM](https://solace.com/products/agent-mesh/)

For more information try these resources:
- Ask the [Solace Community](https://solace.community)
- The Solace Developer Portal website at: https://solace.dev


## Contributing
Contributions are encouraged! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.

## Authors
See the list of [contributors](https://github.com/solacecommunity/solace-agent-mesh-plugins/graphs/contributors) who participated in this project.

## License
See the [LICENSE](LICENSE) file for details.
