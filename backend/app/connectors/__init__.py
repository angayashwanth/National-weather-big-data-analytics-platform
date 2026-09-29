"""
backend/app/connectors/__init__.py

Exposes the Connector base class and the city geocoding table so every
connector can import them from the same place.
"""

from .base import Connector, CITY_TABLE

__all__ = ["Connector", "CITY_TABLE"]
