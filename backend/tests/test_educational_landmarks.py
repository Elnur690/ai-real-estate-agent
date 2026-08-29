import pytest
from app.core.baku_locations import (
    extract_baku_university, extract_all_baku_universities,
    extract_baku_school, extract_all_baku_schools,
    extract_all_educational_institutions,
    extract_metro_station, extract_baku_district, extract_all_locations,
    get_all_aliases_for_location,
    UNIVERSITY_TO_METRO, UNIVERSITY_TO_DISTRICT,
    SCHOOL_TO_METRO, SCHOOL_TO_DISTRICT
)
from app.ai.gemini_provider import GeminiProvider


def test_university_extractions():
    # BDU
    assert extract_baku_university("BDU yaxınlığında kirayə mənzil") == "Bakı Dövlət Universiteti"
    assert extract_baku_university("Bakı Dövlət Universiteti ətrafında obyekt") == "Bakı Dövlət Universiteti"

    # ADNSU / AzII
    assert extract_baku_university("Azİİ yaxınlığında 3 otaqlı mənzil") == "Azərbaycan Dövlət Neft və Sənaye Universiteti"
    assert extract_baku_university("Neft Akademiyası yanında") == "Azərbaycan Dövlət Neft və Sənaye Universiteti"

    # ATU / Tibb
    assert extract_baku_university("Tibb Universiteti yaxınlığında") == "Azərbaycan Tibb Universiteti"
    assert extract_baku_university("Tibb İnstitutunun yanı") == "Azərbaycan Tibb Universiteti"

    # ADA
    assert extract_baku_university("ADA Universiteti ətrafında") == "ADA Universiteti"

    # UNEC / Narxoz
    assert extract_baku_university("UNEC yanı mənzil") == "Azərbaycan Dövlət İqtisad Universiteti"
    assert extract_baku_university("Narxozun yanında kirayə") == "Azərbaycan Dövlət İqtisad Universiteti"

    # AzTU & AzMIU
    assert extract_baku_university("Politexnik yanında ev") == "Azərbaycan Texniki Universiteti"
    assert extract_baku_university("Memarlıq və İnşaat Universiteti ətrafı") == "Azərbaycan Memarlıq və İnşaat Universiteti"

    # ADPU / Pedaqoji
    assert extract_baku_university("Pedaqoji Universitetin yanı") == "Azərbaycan Dövlət Pedaqoji Universiteti"
    assert extract_baku_university("APİ yaxınlığı") == "Azərbaycan Dövlət Pedaqoji Universiteti"

    # ADU / Diller / Inyaz & BSU
    assert extract_baku_university("Dillər Universiteti yaxınlığında") == "Azərbaycan Dillər Universiteti"
    assert extract_baku_university("İnyazın yanı") == "Azərbaycan Dillər Universiteti"
    assert extract_baku_university("Slavyan Universiteti ətrafı") == "Bakı Slavyan Universiteti"

    # BMU / Qafqaz & MAA
    assert extract_baku_university("BMU yaxınlığında Xırdalanda") == "Bakı Mühəndislik Universiteti"
    assert extract_baku_university("Aviasiya Akademiyası yanı") == "Milli Aviasiya Akademiyası"

    # Multiple universities in one string
    all_unis = extract_all_baku_universities("BDU, Azİİ və Slavyan Universiteti yaxınlığında")
    assert "Bakı Dövlət Universiteti" in all_unis
    assert "Azərbaycan Dövlət Neft və Sənaye Universiteti" in all_unis
    assert "Bakı Slavyan Universiteti" in all_unis


def test_school_extractions():
    # Numbered schools
    assert extract_baku_school("23 nömrəli məktəbin yanı") == "23 nömrəli məktəb"
    assert extract_baku_school("160 saylı məktəb yaxınlığı") == "160 nömrəli klassik gimnaziya"
    assert extract_baku_school("6 nömrəli məktəb ətrafı") == "6 nömrəli məktəb"
    assert extract_baku_school("20 nömrəli məktəb-lisey yanı") == "20 nömrəli məktəb"
    assert extract_baku_school("134 nömrəli məktəb") == "134 nömrəli məktəb"
    assert extract_baku_school("189-190 saylı məktəb") == "189-190 nömrəli məktəb"

    # Prominent private & international schools & lyceums
    assert extract_baku_school("Baku Oxford School yaxınlığında villa") == "Bakı Oksford Məktəbi"
    assert extract_baku_school("Avropa Liseyi ətrafında") == "Bakı Avropa Liseyi"
    assert extract_baku_school("Zərifə Əliyeva Liseyi yanı") == "Akademik Zərifə Əliyeva adına Lisey"
    assert extract_baku_school("Landau School yanında kirayə") == "Landau School"
    assert extract_baku_school("TİSA məktəbi yaxınlığında") == "The International School of Azerbaijan"
    assert extract_baku_school("Dünya Məktəbi yanı") == "Dünya Məktəbi"
    assert extract_baku_school("Kaspi Liseyi ətrafı") == "Kaspi Liseyi"
    assert extract_baku_school("Hədəf Liseyi yaxınlığı") == "Hədəf Liseyi"
    assert extract_baku_school("Fizika Riyaziyyat Liseyi yanı") == "Fizika Riyaziyyat Liseyi"


def test_metro_and_district_resolution_from_landmarks():
    # Metro resolution from university
    assert extract_metro_station("BDU yaxınlığında") == "Elmlər Akademiyası"
    assert extract_metro_station("Azİİ ətrafında") == "28 May"
    assert extract_metro_station("Tibb Universiteti yanı") == "Gənclik"
    assert extract_metro_station("ADA Universiteti yaxınlığı") == "Gənclik"
    assert extract_metro_station("UNEC yanında") == "İçərişəhər"
    assert extract_metro_station("Pedaqoji yaxınlığı") == "Sahil"
    assert extract_metro_station("Xəzər Universiteti yanı") == "Neftçilər"

    # Metro resolution from schools
    assert extract_metro_station("160 nömrəli məktəbin yanı") == "28 May"
    assert extract_metro_station("20 nömrəli məktəb yaxınlığı") == "Elmlər Akademiyası"
    assert extract_metro_station("Avropa Liseyi yanı") == "Elmlər Akademiyası"

    # District resolution from universities & schools
    assert extract_baku_district("BDU ətrafında") == "Yasamal"
    assert extract_baku_district("Azİİ yanında") == "Nəsimi"
    assert extract_baku_district("ADA Universiteti") == "Nərimanov"
    assert extract_baku_district("Oxford məktəbi") == "Səbail"
    assert extract_baku_district("BMU yaxınlığında") == "Abşeron"


def test_extract_all_locations_with_schools_and_unis():
    text = "BDU və 23 nömrəli məktəb yaxınlığında 2 otaqlı mənzil"
    locs = extract_all_locations(text)
    assert "Bakı Dövlət Universiteti" in locs
    assert "23 nömrəli məktəb" in locs
    assert "Elmlər Akademiyası" in locs
    assert "28 May" in locs
    assert "Yasamal" in locs


def test_heuristic_parser_with_educational_landmarks():
    gp = GeminiProvider()
    res = gp._heuristic_parse_criteria("Tibb Universiteti yaxınlığında 2 otaqlı kirayə 800 AZN")
    assert res.metro_station == "Gənclik"
    assert res.district == "Nəsimi"
    assert res.offer_type == "rent"
    assert res.min_rooms == 2
    assert res.max_rooms == 2
    assert res.max_price == 800.0


def test_get_all_aliases_includes_educational_landmarks():
    elmler_aliases = get_all_aliases_for_location("Elmlər Akademiyası", is_metro_focus=True)
    assert "bdu" in elmler_aliases
    assert "politexnik" in elmler_aliases
    assert "avropa liseyi" in elmler_aliases

    may28_aliases = get_all_aliases_for_location("28 May", is_metro_focus=True)
    assert "azii" in may28_aliases
    assert "dillər universiteti" in may28_aliases
    assert "160 nömrəli məktəb" in may28_aliases
