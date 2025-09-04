"""
IP Service Utilities for Find My IP Agent

This module provides utility functions and service layer helpers for IP address operations.
"""

import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timezone
# from solace_ai_connector.common.log import log

# Temporary mock for testing
def log_info(*args, **kwargs):
    message = args[0] if args else ""
    print(f"[INFO] {message}")

def log_error(*args, **kwargs):
    message = args[0] if args else ""
    print(f"[ERROR] {message}")

log = type('Log', (), {
    'info': log_info,
    'error': log_error
})()


class IPUtilityService:
    """Utility service for IP address operations."""
    
    def __init__(self):
        self.request_count = 0
        self.last_request_time = None
    
    async def validate_ip_address(self, ip_address: str) -> bool:
        """
        Validate if a string is a valid IP address.
        
        Args:
            ip_address: The IP address string to validate
            
        Returns:
            True if valid IP address, False otherwise
        """
        import re
        
        # IPv4 pattern
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ipv4_pattern, ip_address):
            parts = ip_address.split('.')
            return all(0 <= int(part) <= 255 for part in parts)
        
        # IPv6 pattern (basic)
        ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
        return bool(re.match(ipv6_pattern, ip_address))
    
    def format_location_data(self, location_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format and standardize location data from various APIs.
        
        Args:
            location_data: Raw location data from API
            
        Returns:
            Formatted location data
        """
        formatted = {
            "country": location_data.get("country") or location_data.get("country_name"),
            "region": location_data.get("region") or location_data.get("regionName"),
            "city": location_data.get("city"),
            "latitude": location_data.get("latitude") or location_data.get("lat"),
            "longitude": location_data.get("longitude") or location_data.get("lon"),
            "timezone": location_data.get("timezone"),
            "isp": location_data.get("isp") or location_data.get("org"),
            "postal_code": location_data.get("postal") or location_data.get("zip"),
            "asn": location_data.get("asn") or location_data.get("as")
        }
        
        # Remove None values
        return {k: v for k, v in formatted.items() if v is not None}
    
    def get_request_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the current request session.
        
        Returns:
            Request metadata including count and timestamp
        """
        self.request_count += 1
        self.last_request_time = datetime.now(timezone.utc)
        
        return {
            "request_count": self.request_count,
            "last_request_time": self.last_request_time.isoformat(),
            "session_duration": None  # Could be calculated if needed
        }
    
    async def test_api_connectivity(self, api_url: str) -> Dict[str, Any]:
        """
        Test connectivity to a specific API endpoint.
        
        Args:
            api_url: The API URL to test
            
        Returns:
            Connectivity test results
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    api_url,
                    headers={'User-Agent': 'SAM-find_my_ip/1.0.0'},
                    timeout=5.0
                )
                
                return {
                    "status": "success",
                    "api_url": api_url,
                    "response_time": response.elapsed.total_seconds(),
                    "status_code": response.status_code,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            return {
                "status": "error",
                "api_url": api_url,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
