"""
Default value processing and variable merging
"""

from .product_defaults import ProductDefaultsLoader
from .override_manager import OverrideManager
from .variable_merger import VariableMerger

__all__ = ['ProductDefaultsLoader', 'OverrideManager', 'VariableMerger']