from typing import Optional, List, Dict

BAKU_METRO_STATIONS: Dict[str, List[str]] = {
    "Elmlər Akademiyası": ["elmlər", "elmler", "elmlər akademiyası", "elmler akademiyasi", "elmlər m"],
    "28 May": ["28 may", "28may", "28 may m", "may 28"],
    "Gənclik": ["gənclik", "genclik", "gənclik m", "genclik m"],
    "Nəriman Nərimanov": ["nərimanov", "nerimanov", "n.nərimanov", "nərimanov m"],
    "İnşaatçılar": ["inşaatçılar", "insaatcilar", "inşaatçılar m"],
    "20 Yanvar": ["20 yanvar", "20yanvar", "20 yanvar m"],
    "Memar Əcəmi": ["əcəmi", "ecemi", "memar əcəmi", "memar ecemi"],
    "Nəsimi": ["nəsimi m", "nesimi m", "nəsimi metrosu"],
    "Azadlıq prospekti": ["azadlıq", "azadliq", "azadlıq m", "azadlıq prospekti"],
    "Dərnəgül": ["dərnəgül", "dernegul", "dərnəgül m"],
    "İçərişəhər": ["içərişəhər", "iceriseher", "içəri şəhər", "içərişəhər m"],
    "Sahil": ["sahil", "sahil m", "sahil metrosu"],
    "Nizami": ["nizami m", "nizami metrosu"],
    "Xətai": ["xətai m", "xetai m", "şah ismayıl xətai"],
    "Cəfər Cabbarlı": ["cəfər cabbarlı", "cefer cabbarli"],
    "Ulduz": ["ulduz", "ulduz m"],
    "Koroğlu": ["koroğlu", "koroglu", "məşədi əzizbəyov", "koroğlu m"],
    "Qara Qarayev": ["qara qarayev", "qarayev", "qara qarayev m"],
    "Neftçilər": ["neftçilər", "neftciler", "neftçilər m"],
    "Xalqlar Dostluğu": ["xalqlar", "xalqlar dostluğu", "xalqlar dostlugu", "xalqlar m"],
    "Əhmədli": ["əhmədli", "ehmedli", "əhmədli m"],
    "Həzi Aslanov": ["həzi aslanov", "hezi aslanov", "aslanov"],
    "Avtovağzal": ["avtovağzal", "avtovagzal", "avtovağzal m"],
    "8 Noyabr": ["8 noyabr", "8noyabr", "8 noyabr m"],
    "Xocəsən": ["xocəsən", "xocesen", "xocəsən m"]
}

def extract_metro_station(text: str) -> Optional[str]:
    """Extract Baku Metro station name from text input if present."""
    text_lower = text.lower()
    for station_name, aliases in BAKU_METRO_STATIONS.items():
        for alias in aliases:
            if alias in text_lower:
                return station_name
    return None
