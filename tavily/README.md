# tavily SAM Plugin

An agent for searching the web with tavily ai

[https://www.tavily.com/](https://www.tavily.com/)

This is a plugin for the Solace Agent Mesh (SAM).

## Usage
1. Launch SAM plugin catalog `sam plugin catalog` 
2. Add this repository to your SAM instance if you have not done so already.  `+ Add Registry`, paste in the git repository [https://github.com/solacecommunity/solace-agent-mesh-plugins](https://github.com/solacecommunity/solace-agent-mesh-plugins) with name `Community`
3. Install the Tavily agent using the install button in the gui or with `sam plugin add tavily --plugin tavily`
4. Supply your Tavily mcp server token as `export TAVILY_TOKEN="your_api_key_here"`

You will need a Tavily token from a [free trial](https://www.tavily.com/)

To use the Tavily agent in SAM you will have to ask the orchestrator to find some information on the web and do something with it. 


