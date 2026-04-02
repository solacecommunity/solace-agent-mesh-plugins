"""
Dataiku Agent Plugin for Solace Agent Mesh

This plugin enables invoking Dataiku AI agents through the Solace Agent Mesh ecosystem.
"""

__version__ = "0.1.0"
__author__ = "Solace Community"

from . import tools
from . import lifecycle

__all__ = ["tools", "lifecycle"]