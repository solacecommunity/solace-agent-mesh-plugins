# SendGrid SAM Plugin

SendGrid Agent for sending emails.

## Configuration

The plugin requires the following environment variables to be set:
- `SENDGRID_API_KEY`: Your SendGrid API key.
- `SENDGRID_FROM_EMAIL`: The default sender email address.


## Installation 

To add the SendGrid plugin to your SAM project, run the following command:

```bash
sam plugin add <your-new-component-name> --plugin git+https://github.com/solacecommunity/solace-agent-mesh-plugins#subdirectory=send-grid
```
This will create a new component configuration at `configs/plugins/<your-new-component-name-kebab-case>.yaml`.