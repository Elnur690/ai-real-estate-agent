import re
from typing import Tuple, Optional

# Agency / Broker Detection Keywords
AGENCY_KEYWORDS = [
    "agentlik", "agentliyi", "daşınmaz əmlak", "dasinmaz emlak",
    "əmlak şirkəti", "emlak sirketi", "əmlak ofisi", "emlak ofisi",
    "şirkət", "sirket", "şirkəti", "sirketi", "agent", "vasitəçi (agent)", "vasiteci (agent)",
    "vasitəçi", "vasiteci", "vasitəçilik", "vasitecilik",
    "ofis haqqı", "ofis haqqi", "ofis haqq", "ofis faizi",
    "xidmət haqqı", "xidmet haqqi", "xidmət haqq", "xidmet haqq",
    "komissiya", "komissiyası", "komisiya", "makler", "makler haqqı",
    "rieltor", "realtor", "əmlakçı", "emlakci",
    "şirkətimiz", "filialımız", "elanlarımız",
    "1% ofis", "1% xidmət", "1% xidmet", "2% ofis", "2% xidmət", "2% xidmet",
    "faizlə", "faizle", "depozit tələb", "1-ci ay", "aylıq komissiya"
]

# Commission Percentage Regex Patterns (e.g., 20% ofis haqqı, 30% vasitəçi, 1% xidmət)
COMMISSION_REGEX = re.compile(
    r'(?:\b(?:1|2|3|4|5|10|15|20|25|30|40|50)\s*%\s*(?:ofis|xidmət|xidmet|komissiya|faiz|makler|agentlik|vasitəçi|vasiteci))|'
    r'(?:(?:ofis|xidmət|xidmet|komissiya|makler|agentlik|vasitəçi|vasiteci)\s*(?:haqqı|haqqi|faizi|ödənişi)?\s*[:=-]?\s*(?:1|2|3|4|5|10|15|20|25|30|40|50)\s*%)',
    re.IGNORECASE
)

# Genuine Owner Keywords
OWNER_KEYWORDS = [
    "sahibindən", "sahibinden", "mülkiyyətçidən", "mulkiyyetciden",
    "mülkiyyətçi", "mulkiyyetci", "badge-owner", "owner-badge",
    "öz evimdir", "oz evimdir", "öz mənzilimdir", "oz menzilimdir",
    "öz əmlakımdır", "oz emlakimdir", "vasitəçisiz", "vasitecisiz",
    "maklersiz", "maklerlər narahat etməsin", "maklerler narahat etmesin"
]

# Rental / Deal Type Keywords
RENTAL_KEYWORDS = [
    "kirayə", "kiraye", "icarə", "icare", "arenda", "aylıq", "ayliq",
    "günlük", "gunluk", "sutkalıq", "sutkaliq", "kirayəyə verilir",
    "icarəyə verilir", "kiraye verilir", "icareye verilir", "arendaya verilir",
    "depozit", "komendant daxil", "aylıq ödəniş", "ayliq odenis",
    "/ay", "| ay", "ayliq-"
]

SALE_KEYWORDS = [
    "satılır", "satilir", "satış", "satis", "satiram", "satıram",
    "satışa çıxarıldı", "satisa cixarildi", "ipoteka", "ilkin ödəniş",
    "kupçalı satılır", "kupcali satilir", "nəğd satılır"
]


def classify_property_and_offer(
    title: str = "",
    description: str = "",
    url: str = "",
    raw_text: str = ""
) -> Tuple[str, str, str]:
    """
    Classifies property deal type, category, and seller legitimacy:
    Returns: (offer_type, property_type, seller_type)
    - offer_type: 'sale' | 'rent' | 'daily_rent'
    - property_type: 'apartment' | 'house' | 'office' | 'commercial' | 'land'
    - seller_type: 'agency' | 'owner'
    """
    url_lower = (url or "").lower()
    full_text = f"{title or ''} {description or ''} {url_lower} {raw_text or ''}".lower()

    # 1. Classify Offer Type (Sale vs Rent)
    is_rent_url = any(u in url_lower for u in ["kiraye", "icare", "arenda", "rent", "ayliq", "arenda.az", "leased=true"])
    is_sale_url = any(u in url_lower for u in ["satilir", "satis", "sale", "alqi-satqi", "leased=false"])

    has_rental_kw = any(kw in full_text for kw in RENTAL_KEYWORDS) or is_rent_url
    has_sale_kw = any(kw in full_text for kw in SALE_KEYWORDS) or is_sale_url

    if is_rent_url:
        offer_type = "rent"
    elif is_sale_url and not any(kw in full_text for kw in ["kirayə", "kiraye", "icarə", "icare", "arenda"]):
        offer_type = "sale"
    elif has_rental_kw:
        offer_type = "rent"
    else:
        offer_type = "sale"

    # 2. Classify Property Type
    if "ofis.az" in url_lower or any(u in url_lower for u in ["ofis", "ofisler", "office"]):
        property_type = "office"
    elif any(u in url_lower for u in ["obyekt", "obyektler", "magaza", "restoran", "kommersiya"]):
        property_type = "commercial"
    elif any(u in url_lower for u in ["torpaq", "torpaqlar", "sot-"]):
        property_type = "land"
    elif any(u in url_lower for u in ["heyet-evi", "heyet-evleri", "bag-evi", "bag-evleri", "villa", "villalar"]):
        property_type = "house"
    elif any(k in full_text for k in ["ofis kimi", "ofis icarə", "ofis icare", "ofis üçün", "ofis ucun", "biznes mərkəzi", "biznes merkezi", "plazada ofis", "ofisdir", "ofis satılır", "ofis satilir", "ofis kirayə", "ofis kiraye"]):
        property_type = "office"
    elif any(k in full_text for k in ["obyekt", "mağaza", "magaza", "restoran", "kafe", "klinika", "salon", "anbar", "istehsalat sahəsi", "qeyri-yaşayış", "qeyri yasayis"]):
        property_type = "commercial"
    elif any(k in full_text for k in ["torpaq sahəsi", "torpaq sahesi", "torpaq satılır", "torpaq satilir", "sot torpaq", "hektar"]):
        property_type = "land"
    elif any(k in full_text for k in ["həyət evi", "heyet evi", "bağ evi", "bag evi", "villa", "həyət", "kotec"]):
        property_type = "house"
    else:
        property_type = "apartment"

    # 3. Classify Seller Type (Agency vs Owner)
    has_agency_kw = any(kw in full_text for kw in AGENCY_KEYWORDS) or bool(COMMISSION_REGEX.search(full_text))
    has_owner_kw = any(kw in full_text for kw in OWNER_KEYWORDS)

    # Agency keywords always strictly override owner claims (prevent false "sahibindən" makler postings)
    if has_agency_kw:
        seller_type = "agency"
    elif has_owner_kw:
        seller_type = "owner"
    else:
        # In Baku real estate portals, unmarked listings without verified owner badge are agencies/brokers
        seller_type = "agency"

    return offer_type, property_type, seller_type
