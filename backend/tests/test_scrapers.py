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
        assert isinstance(items, list), f"{scraper.__class__.__name__} did not return a list"
        if items:
            item = items[0]
            assert item.external_id is not None
            assert item.title is not None
            assert item.price >= 0

@pytest.mark.asyncio
async def test_scraper_utils_rotation_and_delays():
    from app.scrapers.utils import get_random_user_agent, get_random_headers, polite_delay
    import time

    ua1 = get_random_user_agent()
    ua2 = get_random_user_agent()
    assert isinstance(ua1, str) and len(ua1) > 20

    headers = get_random_headers(referer="https://bina.az/")
    assert "User-Agent" in headers
    assert headers["Referer"] == "https://bina.az/"
    assert "Accept-Language" in headers

    start = time.time()
    await polite_delay(0.1, 0.2)
    elapsed = time.time() - start
    assert elapsed >= 0.09


@pytest.mark.asyncio
async def test_speed_dial_phone_formatting_and_links():
    from app.core.baku_locations import extract_az_phone
    import re

    # Test Azerbaijani phone extraction from description
    sample_text = "Təcili satılır. Əlaqə: 050-234-56-78. Sahibindən."
    phone_res = extract_az_phone(sample_text)
    assert phone_res is not None
    formatted, raw = phone_res
    assert formatted == "+994 50 234 56 78"
    assert raw == "+994502345678"

    clean_digits = re.sub(r'\D', '', raw)
    assert clean_digits == "994502345678"

    # Verify 1-Tap Speed-Dial and WhatsApp link construction
    tg_contact_line = f"📞 *Əlaqə (1-Tap Zəng):* [{formatted}](tel:{raw})\n💬 *WhatsApp:* [Çat Aç (wa.me)](https://wa.me/{clean_digits})\n"
    wa_contact_line = f"📞 *Zəng et (1-Tap):* {raw}\n💬 *WhatsApp:* https://wa.me/{clean_digits}\n"

    assert "tel:+994502345678" in tg_contact_line
    assert "https://wa.me/994502345678" in tg_contact_line
    assert "+994502345678" in wa_contact_line
    assert "https://wa.me/994502345678" in wa_contact_line


@pytest.mark.asyncio
async def test_bina_az_owner_classification_preservation():
    from app.core.property_classifier import classify_property_and_offer

    # Listing from owner URL without explicit 'sahibinden' keyword in preview
    offer, prop, seller = classify_property_and_offer(
        title="2 otaqlı mənzil 65 m²",
        description="Nizami rayonu, Neftçilər metrosu yaxınlığında təmirli ev",
        url="https://bina.az/items/123456?owner_type=owner",
        existing_seller_type="owner"
    )

    assert offer == "sale"
    assert prop == "apartment"
    assert seller == "owner"


@pytest.mark.asyncio
async def test_commercial_classification_and_owner_landline():
    from app.core.property_classifier import classify_property_and_offer

    # Commercial property classification
    offer, prop, seller = classify_property_and_offer(
        title="Obyekt satılır 290 m²",
        description="Neftçilər metrosu yaxınlığında qeyri-yaşayış sahəsi.",
        url="https://bina.az/items/6389661"
    )
    assert prop == "commercial"

    # Homeowner using landline number with owner keywords
    offer2, prop2, seller2 = classify_property_and_offer(
        title="3 otaqlı mənzil",
        description="Öz evimdir, sahibindən satılır. Əlaqə: 012-456-78-90",
        url="https://bina.az/items/123456?owner_type=owner"
    )
    assert prop2 == "apartment"
    assert seller2 == "owner"

    # Agency with commission
    offer3, prop3, seller3 = classify_property_and_offer(
        title="3 otaqlı mənzil",
        description="Xidmət haqqı 1%, vasitəçi agentlik. Əlaqə: 012-526-94-94",
        url="https://bina.az/items/6389653"
    )
    assert seller3 == "agency"



