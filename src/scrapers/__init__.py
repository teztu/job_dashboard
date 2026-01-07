"""Job scrapers for Norwegian job sites."""

from .arbeidsplassen import ArbeidsplassenScraper
from .base import BaseScraper
from .finn import FinnScraper

__all__ = ["BaseScraper", "FinnScraper", "ArbeidsplassenScraper"]
