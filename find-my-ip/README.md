# Find My IP Agent

A Solace Agent Mesh plugin that provides comprehensive IP address information services including current IP detection, geolocation lookup, and security analysis.

## Overview

The Find My IP agent is designed to help users understand their current network location and connection details. It provides accurate IP address information, geolocation data, and security analysis to support location-based queries and network security assessments.

## Features

This agent provides the following capabilities:

- **Current IP Detection**: Retrieve your current public IP address from reliable APIs
- **Geolocation Services**: Get detailed location information including country, city, region, and coordinates
- **Security Analysis**: Analyze IP addresses for security characteristics including proxy, VPN, TOR, and crawler detection
- **Comprehensive Information**: Provide detailed connection and network information
- **Multi-API Support**: Uses multiple reliable APIs for redundancy and accuracy

## Tools Available

The agent includes the following tools:

- **`get_current_ip`**: Retrieves the current public IP address from reliable APIs
- **`get_ip_with_retry`**: Gets current IP address with retry logic for improved reliability
- **`get_ip_info`**: Retrieves IP address with optional location information
- **`get_ip_comprehensive_info`**: Provides comprehensive IP information including security, connection, and location data
- **`get_ip_security_info`**: Analyzes IP address for security characteristics including proxy, VPN, TOR, and crawler detection
- **`get_ip_location`**: Gets detailed location information for a given IP address using multiple APIs

## Usage Examples

Once the agent is running, you can interact with it using natural language prompts:

### Basic IP Information
- *"What is my current IP address?"*
- *"Show me my public IP"*
- *"Get my IP address"*

### Location-Based Queries
- *"Where am I located?"*
- *"What city am I in?"*
- *"What country is my IP from?"*
- *"Show me my coordinates"*

### Security Analysis
- *"Is my connection secure?"*
- *"Am I using a VPN or proxy?"*
- *"Analyze my IP for security characteristics"*
- *"Check if my IP is flagged as suspicious"*

### Comprehensive Information
- *"Give me all details about my IP"*
- *"Show me comprehensive IP information"*
- *"What are my connection details?"*

### Specific IP Analysis
- *"Where is the IP address 8.8.8.8 located?"*
- *"Analyze the security of IP 192.168.1.1"*
- *"Get location information for 1.1.1.1"*

## APIs and Services Used

This agent utilizes the following external services:

### IP Detection
- **[IPify](https://ipify.org/)**: Free IP address detection service
- **Multiple fallback APIs**: Ensures reliability and availability

### Geolocation Services
- **[ipapi.co](https://ipapi.co/)**: Comprehensive geolocation API
- **[ip-api.com](http://ip-api.com/)**: Free IP geolocation service
- **[ipinfo.io](https://ipinfo.io/)**: IP geolocation and information service
- **[ipwhois.io](https://ipwhois.io/)**: IP geolocation and WHOIS data

### Security Analysis
- **Built-in analysis**: Proxy, VPN, and TOR detection algorithms
- **Multiple data sources**: Cross-referenced security information

## Error Handling

The agent includes robust error handling:

- **Retry Logic**: Automatic retry for failed API calls
- **Fallback APIs**: Multiple API sources for redundancy
- **Graceful Degradation**: Continues operation even if some services are unavailable
- **Clear Error Messages**: Informative error reporting to users

## Limitations

- **Rate Limits**: Some APIs have rate limits (handled automatically)
- **IPv6 Support**: Limited IPv6 support in some APIs
- **Privacy**: IP-based location is approximate and may not reflect exact physical location
- **Network Dependencies**: Requires internet connection for API access

## Contributing

To contribute to this plugin:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

For issues and questions:

1. Check the [Solace Agent Mesh documentation](https://solacelabs.github.io/solace-agent-mesh/)
2. Review existing issues in the repository
3. Create a new issue with detailed information about your problem

## Changelog

### Version 0.1.0
- Initial release
- Basic IP detection and geolocation
- Security analysis capabilities
- Multi-API support for reliability