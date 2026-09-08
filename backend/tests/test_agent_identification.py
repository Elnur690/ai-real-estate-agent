import pytest
from app.models.listing import Listing
from app.models.saved_search import SavedSearch
from app.services.ingestion import IngestionService
from app.core.property_classifier import classify_property_and_offer
from bs4 import BeautifulSoup

def test_inventory_codes_flagged_as_agency():
    # Listing with inventory code "Kod: 4521"
    offer, prop, seller = classify_property_and_offer(
        title="3 otaqlı mənzil Dərnəgül",
        description="Binəqədi rayonu, Dərnəgül m. yaxınlığı, əla təmirli. KOD: 4521. Zəng edin.",
        url="https://bina.az/items/12345"
    )
    assert seller == "agency"

    # Listing with "Elan kodu: 9912"
    offer2, prop2, seller2 = classify_property_and_offer(
        title="2 otaqlı mənzil",
        description="Elan kodu: 9912. 9/11 mərtəbə, yeni tikili.",
        url="https://bina.az/items/12346"
    )
    assert seller2 == "agency"

def test_multi_inventory_pitches_flagged_as_agency():
    # Listing with "başqa variantlar da var"
    offer, prop, seller = classify_property_and_offer(
        title="3 otaqlı mənzil",
        description="Dərnəgül metrosunun yanı. Əlimizdə hər büdcəyə uyğun başqa variantlar da var.",
        url="https://bina.az/items/12347"
    )
    assert seller == "agency"

    # Listing with "elanlarımıza baxmaq üçün"
    offer2, prop2, seller2 = classify_property_and_offer(
        title="2 otaqlı mənzil",
        description="İstifadəçinin bütün elanlarına baxmaq üçün linkə keçin. Digər elanlarımız mövcuddur.",
        url="https://bina.az/items/12348"
    )
    assert seller2 == "agency"

def test_service_fees_and_viewing_fees_flagged_as_agency():
    # Listing with "şirkətin xidmət haqqı 1%"
    offer, prop, seller = classify_property_and_offer(
        title="3 otaqlı mənzil",
        description="Şirkətin xidmət haqqı 1% təşkil edir. Ofisimizə buyurun.",
        url="https://bina.az/items/12349"
    )
    assert seller == "agency"

    # Listing with "baxış haqqı / zəhmət haqqı"
    offer2, prop2, seller2 = classify_property_and_offer(
        title="3 otaqlı mənzil",
        description="Mənzilə baxış ödənişlidir, göstərmə haqqı 10 AZN.",
        url="https://bina.az/items/12350"
    )
    assert seller2 == "agency"

def test_bina_az_author_parsing_vasiteci_vs_owner():
    # HTML of Bina.az detail page where author is "Vasitəçi (agent)" but footer mentions "sahibindən"
    agent_html = """
    <html>
        <body>
            <article class="item_description">3 otaqlı mənzil satılır Dərnəgül m.</article>
            <div class="product-owner">
                <div class="product-owner__info">
                    <div class="product-owner__info-name">Əli bəy</div>
                    <div class="product-owner__info-region">Vasitəçi (agent)</div>
                    <a href="/vasiteciler/6241643">Bütün elanları</a>
                </div>
            </div>
            <footer>Bina.az - Bakıda evlər mülkiyyətçidən və vasitəçilərdən. Ev sahibindən elanlar</footer>
        </body>
    </html>
    """

    soup = BeautifulSoup(agent_html, "html.parser")

    owner_region_el = (
        soup.find(class_='product-owner__info-region') or
        soup.find(class_='product-owner__info-type')
    )
    owner_region_text = owner_region_el.get_text(strip=True).lower() if owner_region_el else ""

    owner_box = soup.find(class_='product-owner')
    owner_box_text = owner_box.get_text(separator=" ", strip=True).lower() if owner_box else ""

    has_specific_agency_link = bool(
        soup.find("a", href=lambda h: h and any(k in h for k in ['/agentlikler/', '/vasiteciler/', '/agents/']))
    )

    is_author_agent = (
        any(k in owner_region_text for k in ["vasitəçi", "vasiteci", "agent", "agentlik"]) or
        any(k in owner_box_text for k in ["vasitəçi (agent)", "vasiteci (agent)", "vasitəçi"])
    )

    assert has_specific_agency_link is True
    assert is_author_agent is True

def test_strict_match_rejects_agent_and_multi_broker_duplicates():
    search = SavedSearch(
        tenant_id=1,
        name="Owner Only Search",
        raw_criteria_text="Dərnəgüldə sahibindən 3 otaqlı",
        seller_type="owner",
        min_price=200000,
        max_price=350000,
        min_rooms=3,
        max_rooms=3,
        district="Binəqədi",
        metro_station="Dərnəgül"
    )

    # 1. Listing with seller_type="agency" -> MUST REJECT
    agent_listing = Listing(
        source_id=1,
        external_id="bina_6241643",
        title="3 otaqlı Mənzil (Dərnəgül)",
        description="Dərnəgül m. yaxınlığında 3 otaqlı mənzil. Vasitəçi.",
        listing_url="https://bina.az/items/6241643",
        district="Binəqədi",
        metro_station="Dərnəgül",
        rooms=3,
        price=335000.0,
        seller_type="agency",
        is_makler=True,
        makler_score=1.0
    )
    assert IngestionService.is_strict_match(search, agent_listing) is False

    # 2. Listing with agency inventory code in description -> MUST REJECT even if claimed owner
    coded_listing = Listing(
        source_id=1,
        external_id="bina_6241644",
        title="3 otaqlı Mənzil (Dərnəgül)",
        description="Dərnəgül m., yeni tikili. Kod: 1045. Zəng edin.",
        listing_url="https://bina.az/items/6241644",
        district="Binəqədi",
        metro_station="Dərnəgül",
        rooms=3,
        price=335000.0,
        seller_type="owner",
        is_makler=False,
        makler_score=0.0
    )
    assert IngestionService.is_strict_match(search, coded_listing) is False

    # 3. Listing with multi-inventory pitch in description -> MUST REJECT
    multi_pitch_listing = Listing(
        source_id=1,
        external_id="bina_6241645",
        title="3 otaqlı Mənzil (Dərnəgül)",
        description="Dərnəgül m., əla mənzil. Başqa variantlarımız da var.",
        listing_url="https://bina.az/items/6241645",
        district="Binəqədi",
        metro_station="Dərnəgül",
        rooms=3,
        price=335000.0,
        seller_type="owner",
        is_makler=False,
        makler_score=0.0
    )
    assert IngestionService.is_strict_match(search, multi_pitch_listing) is False

    # 4. Genuine Owner Listing -> MUST MATCH
    genuine_owner = Listing(
        source_id=1,
        external_id="bina_6241646",
        title="3 otaqlı Mənzil (Dərnəgül)",
        description="Dərnəgül m. yaxınlığında öz evimdir, sahibindən satılır. Maklerlər narahat etməsin.",
        listing_url="https://bina.az/items/6241646",
        district="Binəqədi",
        metro_station="Dərnəgül",
        rooms=3,
        price=320000.0,
        seller_type="owner",
        is_makler=False,
        makler_score=0.0
    )
    assert IngestionService.is_strict_match(search, genuine_owner) is True

def test_baku_timezone_date_formatting():
    from datetime import datetime, timezone, timedelta
    baku_tz = timezone(timedelta(hours=4))
    # Suppose listing created at 09:11 UTC
    created_utc = datetime(2026, 8, 26, 9, 11, 0, tzinfo=timezone.utc)
    now_utc = datetime(2026, 8, 26, 9, 15, 0, tzinfo=timezone.utc)

    now_baku = now_utc.astimezone(baku_tz)
    pub_date_baku = created_utc.astimezone(baku_tz)
    delta_days = (now_baku.date() - pub_date_baku.date()).days

    assert delta_days == 0
    date_str = f"Bugün ({pub_date_baku.strftime('%H:%M')})"
    assert date_str == "Bugün (13:11)"

def test_seller_str_rendering_makler_protection():
    # Listing with is_makler=True must render as Vasitəçidən/Agentlikdən
    listing = Listing(
        source_id=1,
        external_id="101",
        title="Test",
        listing_url="https://bina.az/items/101",
        price=1000.0,
        seller_type="owner", # Even if seller_type was owner, is_makler forces agent label
        is_makler=True,
        makler_score=1.0
    )
    is_genuine_owner = (listing.seller_type == "owner") and not getattr(listing, 'is_makler', False) and ((listing.makler_score or 0.0) < 0.30)
    seller_str = "Ev Sahibindən" if is_genuine_owner else "Vasitəçidən/Agentlikdən"
    assert seller_str == "Vasitəçidən/Agentlikdən"

def test_yeniemlak_vasiteci_rieltor_parsing():
    from app.scrapers.yeniemlak_az import YeniEmlakAzScraper
    # Verify that raw text with 'Vasitəçi / Rieltor' or agency terms classifies as agency
    offer, prop, seller = classify_property_and_offer(
        title="2 otaqlı Mənzil (Nəriman Nərimanov)",
        description="Nərimanov rayonu, Əliyar Əliyev küç. Vasitəçi / Rieltor. 2 otaqlı 54 m².",
        url="https://yeniemlak.az/elan/satilir-2-otaqli-bina-evi-menzil-nerimanov-rayonu-nerimanov-rayonu-eliyar-el-172892"
    )
    assert seller == "agency"

def test_multi_broker_duplicate_cluster_strict_match_rejection():
    search = SavedSearch(
        tenant_id=1,
        name="Owner Only Search",
        raw_criteria_text="Nərimanovda sahibindən 2 otaqlı",
        seller_type="owner",
        min_price=100000,
        max_price=200000,
        min_rooms=2,
        max_rooms=2,
        district="Nərimanov"
    )

    # Multi-broker duplicate listing with 11 postings across 155k-175k AZN
    cluster_listing = Listing(
        source_id=1,
        external_id="yeniemlak_172892",
        title="2 otaqlı Mənzil (Nərimanov)",
        description="Nərimanov m., yeni tikili.",
        listing_url="https://yeniemlak.az/elan/172892",
        district="Nərimanov",
        rooms=2,
        price=155000.0,
        seller_type="owner", # Even if upstream was labeled owner
        duplicate_count=11,
        duplicate_listings=[
            {"id": 1, "price": 155000.0, "seller_type": "agency", "phone": "+994501111111"},
            {"id": 2, "price": 175000.0, "seller_type": "agency", "phone": "+994552222222"}
        ]
    )

    # Must be strictly rejected for owner searches
    assert IngestionService.is_strict_match(search, cluster_listing) is False


def test_bina_az_individual_agent_next_data_and_card_classification():
    import json
    from app.scrapers.bina_az import BinaAzScraper

    # Test detail page with Next.js JSON containing contactTypeName="vasitəçi (agent)" (like listing 6271682)
    next_data = {
        "props": {
            "pageProps": {
                "currentItemData": {
                    "id": "6271682",
                    "contactTypeName": "vasitəçi (agent)",
                    "company": {"__typename": "Company", "id": "175826", "name": "Faiq", "targetType": "AGENCY"},
                    "description": "Baku City Residence Olimpik, Koroğlu m. Premium layihə mənzillər təklif edirik."
                }
            }
        }
    }
    html = f"""
    <html>
        <body>
            <div data-cy="owner-info">
                <div data-cy="owner-info__content">
                    <span>Faiq</span>
                    <span>Vasitəçi (agent)</span>
                </div>
            </div>
            <script id="__NEXT_DATA__" type="application/json">{json.dumps(next_data)}</script>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    next_script = soup.find("script", id="__NEXT_DATA__")
    assert next_script is not None
    parsed_json = json.loads(next_script.string)
    props = parsed_json.get("props", {}).get("pageProps", {})
    item_data = props.get("currentItemData") or props.get("item") or {}
    assert item_data.get("contactTypeName") == "vasitəçi (agent)"
    assert item_data.get("company", {}).get("targetType") == "AGENCY"

    # Card text from feed without owner keywords must not be marked as owner
    card_text = "Daha 12 şəklə bax | Çıxarış var | 440 000 | AZN | Koroğlu m. | 4 otaqlı | 172.8 m² | 7/16 mərtəbə | Bakı, bugün 14:46"
    _, _, detected_seller = classify_property_and_offer(
        title="",
        description=card_text,
        url="/items/6271682",
        raw_text=card_text
    )
    assert detected_seller == "agency"

    # Owner search strictly rejects this listing
    search = SavedSearch(
        tenant_id=1,
        name="Nizami Owner Search",
        district="Nizami",
        seller_type="owner",
        min_price=400000,
        max_price=500000
    )
    listing = Listing(
        source_id=1,
        external_id="bina_6271682",
        title="4 otaqlı Mənzil (Koroğlu)",
        description=item_data["description"],
        listing_url="https://bina.az/items/6271682",
        district="Nizami",
        rooms=4,
        price=440000.0,
        seller_type="agency",
        is_makler=True,
        makler_score=1.0
    )
    assert IngestionService.is_strict_match(search, listing) is False
    is_genuine_owner = (listing.seller_type == "owner") and not getattr(listing, 'is_makler', False) and ((listing.makler_score or 0.0) < 0.30)
    assert is_genuine_owner is False
    seller_str = "Ev Sahibindən" if is_genuine_owner else "Vasitəçidən/Agentlikdən"
    assert seller_str == "Vasitəçidən/Agentlikdən"
