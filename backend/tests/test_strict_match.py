import pytest
from app.models.listing import Listing
from app.models.saved_search import SavedSearch
from app.services.ingestion import IngestionService

def test_strict_match_owner_filtering():
    # Saved search strictly for owner
    search = SavedSearch(
        tenant_id=1,
        name="Owner Only Search",
        raw_criteria_text="Sahibindən mənzil",
        seller_type="owner",
        min_price=100000,
        max_price=200000,
        min_rooms=2,
        max_rooms=3,
        district="Yasamal",
        building_type="new"
    )

    # 1. Authentic owner listing -> MATCH
    owner_listing = Listing(
        source_id=1,
        external_id="101",
        title="Yasamalda 3 otaqlı yeni tikili sahibindən satılır",
        listing_url="https://bina.az/items/101",
        district="Yasamal",
        rooms=3,
        price=150000.0,
        seller_type="owner",
        makler_score=0.0,
        building_type="new"
    )
    assert IngestionService.is_strict_match(search, owner_listing) is True

    # 2. Agency listing with seller_type=agency -> REJECT
    agency_listing = Listing(
        source_id=1,
        external_id="102",
        title="Yasamalda 3 otaqlı yeni tikili",
        listing_url="https://bina.az/items/102",
        district="Yasamal",
        rooms=3,
        price=150000.0,
        seller_type="agency",
        makler_score=0.0,
        building_type="new"
    )
    assert IngestionService.is_strict_match(search, agency_listing) is False

    # 3. Disguised makler with high makler score (>= 0.40) -> REJECT
    disguised_listing = Listing(
        source_id=1,
        external_id="103",
        title="Yasamalda 3 otaqlı yeni tikili",
        listing_url="https://bina.az/items/103",
        district="Yasamal",
        rooms=3,
        price=150000.0,
        seller_type="owner",
        makler_score=0.8,
        building_type="new"
    )
    assert IngestionService.is_strict_match(search, disguised_listing) is False

    # 4. Out-of-bounds price -> REJECT
    expensive_listing = Listing(
        source_id=1,
        external_id="104",
        title="Yasamalda 3 otaqlı yeni tikili sahibindən",
        listing_url="https://bina.az/items/104",
        district="Yasamal",
        rooms=3,
        price=250000.0,
        seller_type="owner",
        makler_score=0.0,
        building_type="new"
    )
    assert IngestionService.is_strict_match(search, expensive_listing) is False

    # 5. Wrong room count -> REJECT
    four_room_listing = Listing(
        source_id=1,
        external_id="105",
        title="Yasamalda 4 otaqlı yeni tikili sahibindən",
        listing_url="https://bina.az/items/105",
        district="Yasamal",
        rooms=4,
        price=150000.0,
        seller_type="owner",
        makler_score=0.0,
        building_type="new"
    )
    assert IngestionService.is_strict_match(search, four_room_listing) is False

    # 6. Wrong district -> REJECT
    other_dist_listing = Listing(
        source_id=1,
        external_id="106",
        title="Nəsimidə 3 otaqlı yeni tikili sahibindən",
        listing_url="https://bina.az/items/106",
        district="Nəsimi",
        rooms=3,
        price=150000.0,
        seller_type="owner",
        makler_score=0.0,
        building_type="new"
    )
    assert IngestionService.is_strict_match(search, other_dist_listing) is False

    # 7. Wrong building type -> REJECT
    old_bld_listing = Listing(
        source_id=1,
        external_id="107",
        title="Yasamalda 3 otaqlı köhnə tikili sahibindən",
        listing_url="https://bina.az/items/107",
        district="Yasamal",
        rooms=3,
        price=150000.0,
        seller_type="owner",
        makler_score=0.0,
        building_type="old"
    )
    assert IngestionService.is_strict_match(search, old_bld_listing) is False

def test_strict_match_multi_location():
    # Saved search with multiple locations (Qarayev, Neftçilər, Xalqlar)
    search = SavedSearch(
        tenant_id=1,
        name="Multi-Location Search",
        raw_criteria_text="Qarayev və Neftçilərdə mənzil",
        seller_type="any",
        metro_station="Qara Qarayev, Neftçilər",
        district="Nizami",
        min_price=80000,
        max_price=160000,
        min_rooms=2,
        max_rooms=3,
        building_type="any"
    )

    # 1. Listing in Qara Qarayev -> MATCH
    qarayev_listing = Listing(
        source_id=1,
        external_id="201",
        title="Qara Qarayev m/st yaxınlığında 2 otaqlı mənzil",
        listing_url="https://bina.az/items/201",
        metro_station="Qara Qarayev",
        district="Nizami",
        rooms=2,
        price=120000.0,
        seller_type="owner",
        makler_score=0.0,
        building_type="new"
    )
    assert IngestionService.is_strict_match(search, qarayev_listing) is True

    # 2. Listing in Neftçilər -> MATCH
    neftchilar_listing = Listing(
        source_id=1,
        external_id="202",
        title="Neftçilər metrosunun yanı 3 otaqlı mənzil",
        listing_url="https://bina.az/items/202",
        metro_station="Neftçilər",
        district="Nizami",
        rooms=3,
        price=140000.0,
        seller_type="agency",
        makler_score=0.2,
        building_type="old"
    )
    assert IngestionService.is_strict_match(search, neftchilar_listing) is True

    # 3. Listing in completely different location (Xırdalan / Abşeron) -> REJECT
    xirdalan_listing = Listing(
        source_id=1,
        external_id="203",
        title="Xırdalanda 2 otaqlı mənzil",
        listing_url="https://bina.az/items/203",
        district="Abşeron",
        metro_station=None,
        rooms=2,
        price=90000.0,
        seller_type="owner",
        makler_score=0.0,
        building_type="new"
    )
    assert IngestionService.is_strict_match(search, xirdalan_listing) is False

def test_strict_match_offer_and_property_type():
    # Saved search: 3-room Apartment for SALE from OWNER in Yasamal
    search = SavedSearch(
        tenant_id=1,
        name="Apartment For Sale Search",
        raw_criteria_text="Yasamalda 3 otaqlı mənzil satılır sahibindən",
        seller_type="owner",
        offer_type="sale",
        property_type="apartment",
        district="Yasamal",
        min_rooms=3,
        max_rooms=3,
        min_price=100000,
        max_price=200000
    )

    # 1. Authentic matching apartment for sale -> MATCH
    good_apartment = Listing(
        source_id=1,
        external_id="301",
        title="Yasamalda 3 otaqlı mənzil satılır",
        listing_url="https://bina.az/items/301",
        district="Yasamal",
        rooms=3,
        price=150000.0,
        seller_type="owner",
        offer_type="sale",
        property_type="apartment",
        makler_score=0.0
    )
    assert IngestionService.is_strict_match(search, good_apartment) is True

    # 2. Office for rent in Yasamal -> MUST REJECT (both offer_type=rent and property_type=office)
    office_rent = Listing(
        source_id=1,
        external_id="302",
        title="Yasamalda 3 otaqlı ofis icarəyə verilir",
        description="Ofis kimi icarəyə verilir, 20% ofis haqqı",
        listing_url="https://ofis.az/items/302",
        district="Yasamal",
        rooms=3,
        price=1200.0,
        seller_type="agency",
        offer_type="rent",
        property_type="office",
        makler_score=1.0
    )
    assert IngestionService.is_strict_match(search, office_rent) is False

    # 3. Apartment for RENT in Yasamal (e.g. 800 AZN / month) -> MUST REJECT
    apartment_rent = Listing(
        source_id=1,
        external_id="303",
        title="Yasamalda 3 otaqlı mənzil kirayə verilir",
        description="Aylıq kirayə 800 AZN",
        listing_url="https://bina.az/items/303",
        district="Yasamal",
        rooms=3,
        price=800.0,
        seller_type="owner",
        offer_type="rent",
        property_type="apartment",
        makler_score=0.0
    )
    assert IngestionService.is_strict_match(search, apartment_rent) is False

    # 4. Office for SALE in Yasamal -> MUST REJECT (property_type is office)
    office_sale = Listing(
        source_id=1,
        external_id="304",
        title="Yasamalda 3 otaqlı ofis satılır",
        description="Plazada ofis satılır",
        listing_url="https://bina.az/items/304",
        district="Yasamal",
        rooms=3,
        price=160000.0,
        seller_type="owner",
        offer_type="sale",
        property_type="office",
        makler_score=0.0
    )
    assert IngestionService.is_strict_match(search, office_sale) is False

    # 5. False Owner claiming "Sahibindən" but mentions agency commission in text -> MUST REJECT
    fake_owner_listing = Listing(
        source_id=1,
        external_id="305",
        title="Yasamalda 3 otaqlı mənzil sahibindən",
        description="Ev sahibindən icazə alınıb, şirkət komissiyası 1%",
        listing_url="https://bina.az/items/305",
        district="Yasamal",
        rooms=3,
        price=150000.0,
        seller_type="agency",
        offer_type="sale",
        property_type="apartment",
        makler_score=1.0
    )
    assert IngestionService.is_strict_match(search, fake_owner_listing) is False

def test_strict_match_multi_rooms_and_both_building_types():
    # Search for 3 or 4 rooms, building_type="any" (matches both new and old buildings)
    search = SavedSearch(
        tenant_id=1,
        name="3 or 4 rooms, any building",
        raw_criteria_text="Nəsimidə 3 və ya 4 otaqlı mənzil",
        seller_type="any",
        offer_type="sale",
        property_type="apartment",
        building_type="any",
        district="Nəsimi",
        min_rooms=3,
        max_rooms=4,
        min_price=100000,
        max_price=300000
    )

    # 1. 3-room in old building -> MATCH
    listing_3_old = Listing(
        source_id=1,
        external_id="401",
        title="Nəsimidə 3 otaqlı köhnə tikili",
        listing_url="https://bina.az/items/401",
        district="Nəsimi",
        rooms=3,
        price=180000.0,
        seller_type="owner",
        offer_type="sale",
        property_type="apartment",
        building_type="old"
    )
    assert IngestionService.is_strict_match(search, listing_3_old) is True

    # 2. 4-room in new building -> MATCH
    listing_4_new = Listing(
        source_id=1,
        external_id="402",
        title="Nəsimidə 4 otaqlı yeni tikili",
        listing_url="https://bina.az/items/402",
        district="Nəsimi",
        rooms=4,
        price=250000.0,
        seller_type="agency",
        offer_type="sale",
        property_type="apartment",
        building_type="new"
    )
    assert IngestionService.is_strict_match(search, listing_4_new) is True

    # 3. 2-room in new building -> REJECT (2 < 3)
    listing_2_new = Listing(
        source_id=1,
        external_id="403",
        title="Nəsimidə 2 otaqlı yeni tikili",
        listing_url="https://bina.az/items/403",
        district="Nəsimi",
        rooms=2,
        price=140000.0,
        seller_type="owner",
        offer_type="sale",
        property_type="apartment",
        building_type="new"
    )
    assert IngestionService.is_strict_match(search, listing_2_new) is False

    # 4. 5-room in old building -> REJECT (5 > 4)
    listing_5_old = Listing(
        source_id=1,
        external_id="404",
        title="Nəsimidə 5 otaqlı köhnə tikili",
        listing_url="https://bina.az/items/404",
        district="Nəsimi",
        rooms=5,
        price=290000.0,
        seller_type="owner",
        offer_type="sale",
        property_type="apartment",
        building_type="old"
    )
    assert IngestionService.is_strict_match(search, listing_5_old) is False

def test_strict_match_historical_lookback():
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)

    # Saved search with 3 months lookback
    search = SavedSearch(
        tenant_id=1,
        name="Aged 3+ months search",
        raw_criteria_text="Nəsimidə 3 otaqlı 3 aydan bəri",
        seller_type="any",
        offer_type="sale",
        property_type="apartment",
        district="Nəsimi",
        min_rooms=3,
        max_rooms=3,
        min_months_on_market=3
    )

    # 1. Listing posted 100 days ago (~3.3 months) -> MATCH
    old_listing = Listing(
        source_id=1,
        external_id="501",
        title="Nəsimidə 3 otaqlı mənzil",
        listing_url="https://bina.az/items/501",
        district="Nəsimi",
        rooms=3,
        price=180000.0,
        seller_type="owner",
        offer_type="sale",
        property_type="apartment",
        created_at=now - timedelta(days=100)
    )
    assert IngestionService.is_strict_match(search, old_listing) is True

    # 2. Fresh listing posted 10 days ago -> REJECT (only 10 days on market < 90 days required)
    fresh_listing = Listing(
        source_id=1,
        external_id="502",
        title="Nəsimidə 3 otaqlı yeni elan",
        listing_url="https://bina.az/items/502",
        district="Nəsimi",
        rooms=3,
        price=180000.0,
        seller_type="owner",
        offer_type="sale",
        property_type="apartment",
        created_at=now - timedelta(days=10)
    )
    assert IngestionService.is_strict_match(search, fresh_listing) is False

def test_strict_match_villa_and_office_types():
    # 1. Villa Search
    villa_search = SavedSearch(
        tenant_id=1,
        name="Villa Search",
        raw_criteria_text="Mərdəkanda villa satılır",
        seller_type="any",
        offer_type="sale",
        property_type="villa",
        district="Mərdəkan"
    )

    villa_listing = Listing(
        source_id=1,
        external_id="601",
        title="Mərdəkanda 5 otaqlı bağ evi / villa satılır",
        listing_url="https://bina.az/items/601",
        district="Xəzər",
        address_raw="Mərdəkan qəsəbəsi",
        rooms=5,
        price=350000.0,
        seller_type="owner",
        offer_type="sale",
        property_type="villa"
    )
    assert IngestionService.is_strict_match(villa_search, villa_listing) is True

    apartment_in_merdekan = Listing(
        source_id=1,
        external_id="602",
        title="Mərdəkanda 2 otaqlı bina evi mənzil",
        listing_url="https://bina.az/items/602",
        district="Xəzər",
        address_raw="Mərdəkan",
        rooms=2,
        price=80000.0,
        seller_type="owner",
        offer_type="sale",
        property_type="apartment"
    )
    assert IngestionService.is_strict_match(villa_search, apartment_in_merdekan) is False

    # 2. Office Search
    office_search = SavedSearch(
        tenant_id=1,
        name="Office Search",
        raw_criteria_text="Nərimanovda ofis kirayə",
        seller_type="any",
        offer_type="rent",
        property_type="office",
        district="Nərimanov"
    )

    office_listing = Listing(
        source_id=1,
        external_id="603",
        title="Nərimanovda plazada ofis icarəyə verilir",
        description="Biznes mərkəzində təmirli ofis sahəsi",
        listing_url="https://ofis.az/items/603",
        district="Nərimanov",
        rooms=4,
        price=2000.0,
        seller_type="agency",
        offer_type="rent",
        property_type="office"
    )
    assert IngestionService.is_strict_match(office_search, office_listing) is True

    residence_listing = Listing(
        source_id=1,
        external_id="604",
        title="Nərimanovda 3 otaqlı yaşayış mənzili kirayə",
        listing_url="https://bina.az/items/604",
        district="Nərimanov",
        rooms=3,
        price=900.0,
        seller_type="owner",
        offer_type="rent",
        property_type="apartment"
    )
    assert IngestionService.is_strict_match(office_search, residence_listing) is False

def test_strict_match_settlement_precision():
    # Badamdar Search (Settlement in Səbail)
    badamdar_search = SavedSearch(
        tenant_id=1,
        name="Badamdar Search",
        raw_criteria_text="Badamdarda 4 otaqlı həyət evi",
        seller_type="any",
        offer_type="sale",
        property_type="house",
        district="Badamdar"
    )

    # 1. Listing in Badamdar -> MATCH
    badamdar_listing = Listing(
        source_id=1,
        external_id="701",
        title="Badamdarda 1-ci massivdə 4 otaqlı həyət evi",
        description="Badamdar qəsəbəsi, gözəl həyəti var",
        listing_url="https://bina.az/items/701",
        district="Səbail",
        address_raw="Badamdar",
        rooms=4,
        price=280000.0,
        seller_type="owner",
        offer_type="sale",
        property_type="house"
    )
    assert IngestionService.is_strict_match(badamdar_search, badamdar_listing) is True

    # 2. Listing in Bayıl (Same Səbail district, but NOT Badamdar!) -> MUST REJECT!
    bayil_listing = Listing(
        source_id=1,
        external_id="702",
        title="Bayılda 4 otaqlı həyət evi",
        description="Bayıl qəsəbəsi, dəniz mənzərəli",
        listing_url="https://bina.az/items/702",
        district="Səbail",
        address_raw="Bayıl",
        rooms=4,
        price=290000.0,
        seller_type="owner",
        offer_type="sale",
        property_type="house"
    )
    assert IngestionService.is_strict_match(badamdar_search, bayil_listing) is False

def test_strict_match_district_hierarchy_and_sublocations():
    # 1. District search for "Nəsimi"
    nesimi_search = SavedSearch(
        tenant_id=1,
        name="Nəsimi Search",
        raw_criteria_text="Nəsimi rayonunda 3 otaqlı",
        district="Nəsimi",
        min_rooms=3,
        max_rooms=3
    )

    # Scraped card from bina.az only says "Memar Əcəmi m." or "28 May m." (district is None) -> MUST MATCH!
    ecemi_listing = Listing(
        source_id=1,
        external_id="801",
        title="3 otaqlı mənzil 175000 AZN (Memar Əcəmi)",
        description="Bina.az: Memar Əcəmi m. | 3 otaqlı | 85 m² | 4/5 mərtəbə",
        listing_url="https://bina.az/items/801",
        metro_station="Memar Əcəmi",
        district=None,
        rooms=3,
        price=175000.0,
        building_type="new",
        seller_type="owner",
        offer_type="sale",
        property_type="apartment"
    )
    assert IngestionService.is_strict_match(nesimi_search, ecemi_listing) is True

    # 2. District search for "Yasamal"
    yasamal_search = SavedSearch(
        tenant_id=1,
        name="Yasamal Search",
        raw_criteria_text="Yasamalda 2 otaqlı",
        district="Yasamal",
        min_rooms=2,
        max_rooms=2
    )

    # Scraped card says "Elmlər Akademiyası m." (district is None) -> MUST MATCH!
    elmler_listing = Listing(
        source_id=1,
        external_id="802",
        title="2 otaqlı mənzil 140000 AZN (Elmlər)",
        description="Bina.az: Elmlər Akademiyası m. | 2 otaqlı | 60 m²",
        listing_url="https://bina.az/items/802",
        metro_station="Elmlər Akademiyası",
        district=None,
        rooms=2,
        price=140000.0,
        building_type="new",
        seller_type="owner",
        offer_type="sale",
        property_type="apartment"
    )
    assert IngestionService.is_strict_match(yasamal_search, elmler_listing) is True


