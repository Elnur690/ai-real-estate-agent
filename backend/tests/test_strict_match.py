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
