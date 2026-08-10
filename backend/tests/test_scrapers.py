import pytest
from app.scrapers.bina_az import BinaAzScraper
from app.scrapers.tap_az import TapAzScraper
from app.scrapers.yeniemlak_az import YeniEmlakAzScraper
from app.scrapers.evonline_az import EvOnlineAzScraper
from app.scrapers.ev10_az import Ev10AzScraper
from app.scrapers.vipemlak_az import VipEmlakAzScraper
from app.scrapers.ofis_az import OfisAzScraper
from app.scrapers.kub_az import KubAzScraper
from app.scrapers.lalafo_az import LalafoAzScraper
from app.scrapers.homdom_az import HomDomAzScraper
from app.scrapers.rahatemlak_az import RahatEmlakAzScraper
from app.scrapers.unvan_az import UnvanAzScraper
from app.scrapers.ipoteka_az import IpotekaAzScraper
from app.scrapers.binam_az import BinamAzScraper
from app.scrapers.binalar_az import BinalarAzScraper
from app.scrapers.mulk_az import MulkAzScraper
from app.scrapers.villa_az import VillaAzScraper

@pytest.mark.asyncio
async def test_all_scrapers_return_valid_items():
    scrapers = [
        BinaAzScraper(),
        TapAzScraper(),
        YeniEmlakAzScraper(),
        EvOnlineAzScraper(),
        Ev10AzScraper(),
        VipEmlakAzScraper(),
        OfisAzScraper(),
        KubAzScraper(),
        LalafoAzScraper(),
        HomDomAzScraper(),
        RahatEmlakAzScraper(),
        UnvanAzScraper(),
        IpotekaAzScraper(),
        BinamAzScraper(),
        BinalarAzScraper(),
        MulkAzScraper(),
        VillaAzScraper()
    ]

    for scraper in scrapers:
        items = await scraper.scrape_source("http://example.com")
        assert len(items) > 0, f"{scraper.__class__.__name__} returned no items"
        item = items[0]
        assert item.external_id is not None
        assert item.title is not None
        assert item.price >= 0
