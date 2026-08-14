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
