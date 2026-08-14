from typing import Optional, List, Dict

BAKU_METRO_STATIONS: Dict[str, List[str]] = {
    "Elmlər Akademiyası": ["elmlər", "elmler", "elmlər akademiyası", "elmler akademiyasi", "elmlər m", "elmler m", "bdu", "hüseyn cavid", "huseyn cavid"],
    "28 May": ["28 may", "28may", "28 may m", "may 28", "vağzal", "dilarə əliyeva", "28 mall", "28 mol"],
    "Gənclik": ["gənclik", "genclik", "gənclik m", "genclik m", "gənclik mall", "genclik mall", "zoopark", "tibb universiteti", "koroglu heykeli"],
    "Nəriman Nərimanov": ["nərimanov", "nerimanov", "n.nərimanov", "nərimanov m", "nerimanov m", "montin", "metropark", "life centre"],
    "İnşaatçılar": ["inşaatçılar", "insaatcilar", "inşaatçılar m", "insaatcilar m", "qələbə dairəsi", "qelebe dairesi", "şərifzadə", "serifzade", "ats"],
    "20 Yanvar": ["20 yanvar", "20yanvar", "20 yanvar m", "velotrek", "onkoloji", "respublika xəstəxanası"],
    "Memar Əcəmi": ["əcəmi", "ecemi", "memar əcəmi", "memar ecemi", "əcəmi m", "ecemi m", "3-cü mkr", "4-cü mkr", "5-ci mkr"],
    "Nəsimi": ["nəsimi m", "nesimi m", "nəsimi metrosu", "nesimi metrosu", "zarifa aliyeva parki"],
    "Azadlıq prospekti": ["azadlıq", "azadliq", "azadlıq m", "azadliq m", "azadlıq prospekti", "azadliq prospekti", "azadlıq metrosu", "azadliq metrosu", "8-ci mikrorayon", "8 ci mkr", "8-ci mkr", "7-ci mikrorayon", "7 ci mkr", "7-ci mkr"],
    "Dərnəgül": ["dərnəgül", "dernegul", "dərnəgül m", "dernegul m", "6-cı mkr", "6 ci mkr", "9-cu mkr", "9 ci mkr"],
    "İçərişəhər": ["içərişəhər", "iceriseher", "içəri şəhər", "iceri seher", "içərişəhər m", "axundov bağı", "governor", "fountain square"],
    "Sahil": ["sahil", "sahil m", "sahil metrosu", "bulvar", "tarqovi", "fəvvarələr", "torqoviy", "pedaqoji"],
    "Nizami": ["nizami m", "nizami metrosu", "qış parkı", "qis parki", "nizami kinoteatri", "beşmərtəbə"],
    "Xətai": ["xətai m", "xetai m", "xətai metrosu", "şah ismayıl xətai", "sah ismayil xetai", "ağ şəhər", "ag seher", "ali mehkeme"],
    "Cəfər Cabbarlı": ["cəfər cabbarlı", "cefer cabbarli", "c.cabbarlı"],
    "Ulduz": ["ulduz", "ulduz m", "ulduz metrosu"],
    "Koroğlu": ["koroğlu", "koroglu", "koroğlu m", "koroglu m", "məşədi əzizbəyov", "azik"],
    "Qara Qarayev": ["qara qarayev", "qarayev", "qara qarayev m", "qarayev m", "planet"],
    "Neftçilər": ["neftçilər", "neftciler", "neftçilər m", "neftciler m", "intertibb", "icra hakimiyyəti"],
    "Xalqlar Dostluğu": ["xalqlar", "xalqlar dostluğu", "xalqlar dostlugu", "xalqlar m", "laçın", "babək prospekti"],
    "Əhmədli": ["əhmədli", "ehmedli", "əhmədli m", "ehmedli m", "sarayevo", "baku medical plaza"],
    "Həzi Aslanov": ["həzi aslanov", "hezi aslanov", "aslanov", "aslanov m", "həzi aslanov m", "kvadratlar"],
    "Avtovağzal": ["avtovağzal", "avtovagzal", "avtovağzal m", "avtovagzal m", "beynəlxalq avtovağzal"],
    "8 Noyabr": ["8 noyabr", "8noyabr", "8 noyabr m", "8 noyabr metrosu", "hərbi hospital"],
    "Xocəsən": ["xocəsən", "xocesen", "xocəsən m", "xocesen m"]
}

# Baku Metro Lines Network Adjacency Graph (1-stop neighboring stations)
METRO_ADJACENCY: Dict[str, List[str]] = {
    "Dərnəgül": ["Azadlıq prospekti"],
    "Azadlıq prospekti": ["Dərnəgül", "Nəsimi"],
    "Nəsimi": ["Azadlıq prospekti", "Memar Əcəmi"],
    "Memar Əcəmi": ["Nəsimi", "20 Yanvar", "8 Noyabr", "Avtovağzal"],
    "20 Yanvar": ["Memar Əcəmi", "İnşaatçılar"],
    "İnşaatçılar": ["20 Yanvar", "Elmlər Akademiyası"],
    "Elmlər Akademiyası": ["İnşaatçılar", "Nizami"],
    "Nizami": ["Elmlər Akademiyası", "28 May"],
    "28 May": ["Nizami", "Gənclik", "Sahil", "Cəfər Cabbarlı"],
    "Cəfər Cabbarlı": ["28 May", "Xətai"],
    "Sahil": ["28 May", "İçərişəhər"],
    "İçərişəhər": ["Sahil"],
    "Gənclik": ["28 May", "Nəriman Nərimanov"],
    "Nəriman Nərimanov": ["Gənclik", "Ulduz"],
    "Ulduz": ["Nəriman Nərimanov", "Koroğlu"],
    "Koroğlu": ["Ulduz", "Qara Qarayev"],
    "Qara Qarayev": ["Koroğlu", "Neftçilər"],
    "Neftçilər": ["Qara Qarayev", "Xalqlar Dostluğu"],
    "Xalqlar Dostluğu": ["Neftçilər", "Əhmədli"],
    "Əhmədli": ["Xalqlar Dostluğu", "Həzi Aslanov"],
    "Həzi Aslanov": ["Əhmədli"],
    "8 Noyabr": ["Memar Əcəmi", "Avtovağzal"],
    "Avtovağzal": ["8 Noyabr", "Memar Əcəmi", "Xocəsən"],
    "Xocəsən": ["Avtovağzal"],
    "Xətai": ["Cəfər Cabbarlı", "28 May"]
}

BAKU_DISTRICTS: Dict[str, List[str]] = {
    "Binəqədi": [
        "binəqədi", "bineqedi", "azadlıq", "azadliq", "dərnəgül", "dernegul", "biləcəri", "bileceri",
        "sulutəpə", "sulutepe", "rəsulzadə", "resulzade", "xutor", "m.ə.rəsulzadə", "28 may qəs",
        "6-cı mikrorayon", "7-ci mikrorayon", "8-ci mikrorayon", "9-cu mikrorayon",
        "6-cı mkr", "7-ci mkr", "8-ci mkr", "9-cu mkr", "6 ci mkr", "7 ci mkr", "8 ci mkr", "9 ci mkr"
    ],
    "Nəsimi": [
        "nəsimi", "nesimi", "28 may", "memar əcəmi", "ecemi", "tibbi", "sirk", "papanin",
        "1-ci mikrorayon", "2-ci mikrorayon", "3-cü mikrorayon", "4-cü mikrorayon", "5-ci mikrorayon",
        "1-ci mkr", "2-ci mkr", "3-cü mkr", "4-cü mkr", "5-ci mkr", "1 ci mkr", "2 ci mkr", "3 ci mkr", "4 ci mkr", "5 ci mkr"
    ],
    "Yasamal": [
        "yasamal", "yeni yasamal", "elmlər", "elmler", "inşaatçılar", "insaatcilar", "şərifzadə", "serifzade",
        "hüseyn cavid", "musabəyov", "musabeyov", "tbilisi", "sovet", "izmir", "almaz park", "kristal abseron yasamal"
    ],
    "Xətai": [
        "xətai", "xetai", "həzi aslanov", "hezi aslanov", "əhmədli", "ehmedli", "köhnə günəşli", "kohne gunesli",
        "ağ şəhər", "ag seher", "nzs", "upd", "nobel", "8 noyabr pr", "megafun", "baku white city"
    ],
    "Nərimanov": [
        "nərimanov", "nerimanov", "gənclik", "genclik", "montin", "təhsil nazirliyi", "kosmos", "böyükşor",
        "ağa nemətulla", "aga nemetulla", "tebriz kucesi", "təbriz küçəsi", "heydər əliyev mərkəzi"
    ],
    "Səbail": [
        "səbail", "sebail", "içərişəhər", "iceriseher", "sahil", "bayıl", "bayil", "badamdar",
        "20-ci sahə", "şıxov", "sixov", "torqoviy", "fountain square", "port baku"
    ],
    "Nizami": [
        "nizami r", "nizami rayonu", "neftçilər", "neftciler", "qara qarayev", "qarayev", "xalqlar",
        "8-ci kilometr", "8 km", "8-ci km", "keşlə", "kesle", "babək", "babek"
    ],
    "Sabunçu": [
        "sabunçu", "sabuncu", "bakıxanov", "bakixanov", "razin", "zabrat", "bilgəh", "kürdəxanı",
        "maştağa", "mastaga", "nardaran", "pirşağı", "pirsagi", "ramana", "balaxanı", "balaxani"
    ],
    "Suraxanı": [
        "suraxanı", "suraxani", "qaraçuxur", "qaracuxur", "yeni günəşli", "yeni gunesli", "əmircan",
        "emircan", "bülbülə", "bulbule", "hövsan", "hovsan", "ziğ", "zig", "bahar"
    ],
    "Xəzər": [
        "xəzər", "xezer", "mərdəkan", "merdekan", "şüvəlan", "suvelan", "buzovna", "binə qəs",
        "bine qes", "türkan", "turkan", "zirə", "zire", "qala", "şaqan", "saqan"
    ],
    "Abşeron": [
        "abşeron", "abseron", "xırdalan", "xirdalan", "masazır", "masazir", "saray", "novxanı",
        "novxani", "qobu", "hökməli", "hokmeli", "mehdiabad", "fatmayı", "fatmayi", "digah", "məmədli", "məhəmmədi"
    ],
    "Sumqayıt": [
        "sumqayıt", "sumqayit", "corat", "hacı zeynalabdin", "sumqayit bulvar", "sumqayıt bulvarı"
    ],
    "Qaradağ": [
        "qaradağ", "qaradag", "lökbatan", "lokbatan", "sahil qəs", "puta", "qobustan qəs", "səngəçal", "sengecal"
    ],
    "Pirallahi": [
        "pirallahi", "gürgən", "gurgen", "çilov", "neft daşları"
    ]
}

# Baku Adjacent Geographical Neighboring Districts
DISTRICT_ADJACENCY: Dict[str, List[str]] = {
    "Binəqədi": ["Nəsimi", "Nərimanov", "Abşeron"],
    "Nəsimi": ["Yasamal", "Binəqədi", "Nərimanov", "Səbail"],
    "Yasamal": ["Nəsimi", "Səbail", "Binəqədi", "Abşeron"],
    "Səbail": ["Yasamal", "Nəsimi", "Xətai", "Qaradağ"],
    "Nərimanov": ["Nəsimi", "Binəqədi", "Nizami", "Xətai"],
    "Nizami": ["Nərimanov", "Xətai", "Sabunçu", "Suraxanı"],
    "Xətai": ["Nərimanov", "Nizami", "Suraxanı", "Səbail"],
    "Sabunçu": ["Nizami", "Suraxanı", "Abşeron", "Xəzər"],
    "Suraxanı": ["Xətai", "Nizami", "Sabunçu", "Xəzər"],
    "Xəzər": ["Sabunçu", "Suraxanı", "Pirallahi"],
    "Abşeron": ["Binəqədi", "Yasamal", "Sabunçu", "Sumqayıt", "Qaradağ"],
    "Sumqayıt": ["Abşeron"],
    "Qaradağ": ["Səbail", "Yasamal", "Abşeron"],
    "Pirallahi": ["Xəzər"]
}

def extract_metro_station(text: str) -> Optional[str]:
    """Extract Baku Metro station name from text input if present."""
    if not text:
        return None
    text_lower = text.lower()
    for station_name, aliases in BAKU_METRO_STATIONS.items():
        for alias in aliases:
            if alias in text_lower:
                return station_name
    return None

def extract_baku_district(text: str) -> Optional[str]:
    """Extract official Baku district name from text input. Returns None if no district found."""
    if not text:
        return None
    text_lower = text.lower()
    for dist_name, keywords in BAKU_DISTRICTS.items():
        for kw in keywords:
            if kw in text_lower:
                return dist_name
    return None

def is_adjacent_metro(target_metro: str, candidate_metro: str) -> bool:
    """Returns True if candidate_metro is an immediate 1-stop neighbor of target_metro."""
    if not target_metro or not candidate_metro:
        return False
    neighbors = METRO_ADJACENCY.get(target_metro, [])
    return candidate_metro in neighbors

def is_adjacent_district(target_district: str, candidate_district: str) -> bool:
    """Returns True if candidate_district is an immediate geographical neighbor of target_district."""
    if not target_district or not candidate_district:
        return False
    neighbors = DISTRICT_ADJACENCY.get(target_district, [])
    return candidate_district in neighbors
