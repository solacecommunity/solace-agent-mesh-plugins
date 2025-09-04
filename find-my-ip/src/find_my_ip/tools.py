"""
Find My IP Agent Tools

This module contains the tools for the Find My IP Agent following SAM patterns.
"""

import httpx
from typing import Any, Dict, Optional
from datetime import datetime, timezone
# from google.adk.tools import ToolContext
# from solace_ai_connector.common.log import log

# Temporary mock for testing
class ToolContext:
    pass

def log_info(*args, **kwargs):
    message = args[0] if args else ""
    print(f"[INFO] {message}")

def log_error(*args, **kwargs):
    message = args[0] if args else ""
    print(f"[ERROR] {message}")

def log_warning(*args, **kwargs):
    message = args[0] if args else ""
    print(f"[WARNING] {message}")

log = type('Log', (), {
    'info': log_info,
    'error': log_error,
    'warning': log_warning
})()


async def get_current_ip(
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get current IP address from IPify API.
    
    Returns:
        Dict containing IP address information or error details
    """
    log.info("[GetCurrentIP] Getting current IP address from IPify API")
    
    api_url = "https://api.ipify.org?format=json"
    
    try:
        # Fetch IP address data
        async with httpx.AsyncClient() as client:
            response = await client.get(
                api_url,
                headers={'User-Agent': 'SAM-find_my_ip/1.0.0'},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
        
        ip_address = data.get("ip")
        if not ip_address:
            raise ValueError("No IP address found in API response")
        
        result = {
            "status": "success",
            "ip_address": ip_address,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "ipify-api",
            "api_url": api_url
        }
        
        log.info(f"[GetCurrentIP] Successfully retrieved IP: {ip_address}")
        return result
        
    except httpx.RequestError as e:
        log.error(f"[GetCurrentIP] Network error: {e}")
        return {
            "status": "error",
            "message": f"Network error: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": "network_error"
        }
    except httpx.HTTPStatusError as e:
        log.error(f"[GetCurrentIP] HTTP error {e.response.status_code}: {e}")
        return {
            "status": "error",
            "message": f"HTTP error {e.response.status_code}: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": "http_error"
        }
    except (ValueError, KeyError) as e:
        log.error(f"[GetCurrentIP] Data processing error: {e}")
        return {
            "status": "error",
            "message": f"Data processing error: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": "data_error"
        }
    except Exception as e:
        log.error(f"[GetCurrentIP] Unexpected error: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": "unknown_error"
        }


async def get_ip_with_retry(
    max_retries: int = 3,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get current IP address with retry logic for improved reliability.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
    
    Returns:
        Dict containing IP address information or error details
    """
    log.info(f"[GetIPWithRetry] Getting IP address with up to {max_retries} retries")
    
    for attempt in range(max_retries):
        try:
            result = await get_current_ip(tool_context, tool_config)
            
            if result["status"] == "success":
                log.info(f"[GetIPWithRetry] Successfully retrieved IP on attempt {attempt + 1}")
                return result
            
            log.warning(f"[GetIPWithRetry] Attempt {attempt + 1} failed: {result['message']}")
            
        except Exception as e:
            log.error(f"[GetIPWithRetry] Attempt {attempt + 1} error: {e}")
        
        # Wait before retry (exponential backoff)
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt
            log.info(f"[GetIPWithRetry] Waiting {wait_time} seconds before retry")
            import asyncio
            await asyncio.sleep(wait_time)
    
    return {
        "status": "error",
        "message": f"Failed to retrieve IP address after {max_retries} attempts",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error_type": "max_retries_exceeded"
    }


async def get_ip_info(
    include_location: bool = False,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get current IP address with optional location information.
    
    Args:
        include_location: Whether to include location information (default: False)
    
    Returns:
        Dict containing IP address and optional location information
    """
    log.info(f"[GetIPInfo] Getting IP information (location: {include_location})")
    
    # Get basic IP information
    ip_result = await get_current_ip(tool_context, tool_config)
    
    if ip_result["status"] != "success":
        return ip_result
    
    result = {
        "status": "success",
        "ip_address": ip_result["ip_address"],
        "timestamp": ip_result["timestamp"],
        "source": ip_result["source"],
        "location_info": None
    }
    
    # Add location information if requested
    if include_location:
        try:
            location_result = await get_ip_location(ip_result["ip_address"], tool_context, tool_config)
            if location_result["status"] == "success":
                result["location_info"] = location_result["data"]
            else:
                result["location_warning"] = location_result["message"]
        except Exception as e:
            log.warning(f"[GetIPInfo] Failed to get location info: {e}")
            result["location_warning"] = f"Location lookup failed: {str(e)}"
    
    return result


async def get_ip_comprehensive_info(
    ip_address: str,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get comprehensive IP information including security, connection, and detailed location data.
    
    Args:
        ip_address: The IP address to look up
    
    Returns:
        Dict containing comprehensive IP information
    """
    log.info(f"[GetIPComprehensiveInfo] Getting comprehensive info for IP: {ip_address}")
    
    # Get basic location info first
    location_result = await get_ip_location(ip_address, tool_context, tool_config)
    
    # Try to get additional security and connection info
    security_info = await get_ip_security_info(ip_address, tool_context, tool_config)
    
    result = {
        "status": "success",
        "ip_address": ip_address,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "location": location_result.get("data") if location_result["status"] == "success" else None,
        "security": security_info.get("data") if security_info["status"] == "success" else None,
        "apis_used": {
            "location": location_result.get("api_used", "unknown"),
            "security": security_info.get("api_used", "unknown")
        }
    }
    
    return result


async def get_ip_security_info(
    ip_address: str,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get security and connection information for an IP address using multiple APIs.
    
    Args:
        ip_address: The IP address to look up
    
    Returns:
        Dict containing security information
    """
    log.info(f"[GetIPSecurityInfo] Getting security info for IP: {ip_address}")
    
    # Try multiple APIs for security info with fallback
    security_apis = [
        {
            "name": "ipwhois.io",
            "url": f"https://ipwhois.app/json/{ip_address}",
            "parser": lambda data: {
                "asn": data.get("connection", {}).get("asn"),
                "isp": data.get("connection", {}).get("isp"),
                "org": data.get("connection", {}).get("org"),
                "is_proxy": data.get("security", {}).get("proxy", False),
                "is_vpn": data.get("security", {}).get("vpn", False),
                "is_tor": data.get("security", {}).get("tor", False),
                "is_crawler": data.get("security", {}).get("crawler", False)
            }
        },

        {
            "name": "ip-api.com",
            "url": f"http://ip-api.com/json/{ip_address}",
            "parser": lambda data: {
                "asn": data.get("as"),
                "isp": data.get("isp"),
                "org": data.get("org"),
                "is_proxy": False,  # Not provided by this API
                "is_vpn": False,    # Not provided by this API
                "is_tor": False     # Not provided by this API
            }
        }
    ]
    
    for api in security_apis:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    api["url"],
                    headers={'User-Agent': 'SAM-find_my_ip/1.0.0'},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
            
            security_info = api["parser"](data)
            security_info["api_source"] = api["name"]
            
            return {
                "status": "success",
                "data": security_info,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "api_used": api["name"]
            }
            
        except Exception as e:
            log.warning(f"[GetIPSecurityInfo] Failed with {api['name']}: {e}")
            continue
    
    # If all APIs fail
    log.error(f"[GetIPSecurityInfo] All security APIs failed for IP: {ip_address}")
    return {
        "status": "error",
        "message": "All security APIs failed",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


async def get_ip_location(
    ip_address: str,
    tool_context: Optional[ToolContext] = None,
    tool_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get location information for an IP address using multiple APIs for redundancy.
    
    Args:
        ip_address: The IP address to look up
    
    Returns:
        Dict containing location information
    """
    log.info(f"[GetIPLocation] Getting location for IP: {ip_address}")
    
    # Try multiple APIs for redundancy
    apis = [
        {
            "name": "ipapi.co",
            "url": f"https://ipapi.co/{ip_address}/json/",
            "parser": lambda data: {
                "country": data.get("country_name"),
                "region": data.get("region"),
                "city": data.get("city"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "timezone": data.get("timezone"),
                "isp": data.get("org"),
                "postal_code": data.get("postal")
            }
        },
        {
            "name": "ip-api.com",
            "url": f"http://ip-api.com/json/{ip_address}",
            "parser": lambda data: {
                "country": data.get("country"),
                "region": data.get("regionName"),
                "city": data.get("city"),
                "latitude": data.get("lat"),
                "longitude": data.get("lon"),
                "timezone": data.get("timezone"),
                "isp": data.get("isp"),
                "postal_code": data.get("zip"),
                "asn": data.get("as")
            }
        },
        {
            "name": "ipinfo.io",
            "url": f"https://ipinfo.io/{ip_address}/json",
            "parser": lambda data: {
                "country": data.get("country"),
                "region": data.get("region"),
                "city": data.get("city"),
                "latitude": data.get("loc", "").split(",")[0] if data.get("loc") else None,
                "longitude": data.get("loc", "").split(",")[1] if data.get("loc") else None,
                "timezone": data.get("timezone"),
                "isp": data.get("org"),
                "postal_code": data.get("postal")
            }
        },
        {
            "name": "ipwhois.io",
            "url": f"https://ipwhois.app/json/{ip_address}",
            "parser": lambda data: {
                "country": data.get("country"),
                "region": data.get("region"),
                "city": data.get("city"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "timezone": data.get("timezone", {}).get("id") if data.get("timezone") else None,
                "isp": data.get("connection", {}).get("isp") if data.get("connection") else None,
                "asn": data.get("connection", {}).get("asn") if data.get("connection") else None,
                "security": data.get("security", {})
            }
        },

    ]
    
    for api in apis:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    api["url"],
                    headers={'User-Agent': 'SAM-find_my_ip/1.0.0'},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
            
            location_info = api["parser"](data)
            
            # Add API source information
            location_info["api_source"] = api["name"]
            
            return {
                "status": "success",
                "data": location_info,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "api_used": api["name"]
            }
            
        except Exception as e:
            log.warning(f"[GetIPLocation] Failed with {api['name']}: {e}")
            continue
    
    # If all APIs fail
    log.error(f"[GetIPLocation] All APIs failed for IP: {ip_address}")
    return {
        "status": "error",
        "message": "All location APIs failed",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
