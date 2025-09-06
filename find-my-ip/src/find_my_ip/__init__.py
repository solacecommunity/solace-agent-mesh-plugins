"""Find My IP SAM Plugin Package

This package provides comprehensive IP address information services including
current IP detection, geolocation, security analysis, and connection details.
"""

__version__ = "0.1.0"
__author__ = "Giri Venkatesan"
__email__ = "giri.venkatesan@solace.com"

# Import main tools for easy access
from .tools import (
    get_current_ip,
    get_ip_with_retry,
    get_ip_info,
    get_ip_comprehensive_info,
    get_ip_security_info,
    get_ip_location
)

# Import utility services
from .services import IPUtilityService

__all__ = [
    "get_current_ip",
    "get_ip_with_retry", 
    "get_ip_info",
    "get_ip_comprehensive_info",
    "get_ip_security_info",
    "get_ip_location",
    "IPUtilityService"
]
