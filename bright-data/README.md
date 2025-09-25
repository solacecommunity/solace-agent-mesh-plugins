# bright-data SAM Plugin

An agent to discover, access, extract and interact with any public website via brighdata

https://brightdata.com/

This is a plugin for the Solace Agent Mesh (SAM).

## Usage
1. Launch SAM plugin catalog `sam plugin catalog` 
2. Add this repository to your SAM instance if you have not done so already.  `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the Bright Data agent using the install button in the gui or with `sam plugin add bright-data --plugin bright-data`
4. Supply your bright-data mcp server token as `export BRIGHTDATA_TOKEN="your_api_key_here"`

Obtain a Bright Data token by starting a [free trial](https://brightdata.com/)

To use BrightData in SAM you will have to make a request for data from the web via the orchestrator 
  
## Installation 

To add the Bright Data plugin to your SAM project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=bright-data
```
This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.