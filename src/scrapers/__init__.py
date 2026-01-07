"""Job scrapers for Norwegian job sites."""

from .base import BaseScraper
from .finn import FinnScraper
from .arbeidsplassen import ArbeidsplassenScraper

__all__ = ["BaseScraper", "FinnScraper", "ArbeidsplassenScraper"]
