"""Constantes pour l'intégration Congés scolaires FW-B."""
from datetime import timedelta

DOMAIN = "wallonie_school_holidays"

# Page officielle listant les liens vers les calendriers .ics
CALENDAR_PAGE_URL = "https://www.enseignement.be/calendrier-scolaire"

# Types de calendrier disponibles sur le site, avec le motif présent dans le
# nom de fichier .ics permettant de les identifier.
CALENDAR_TYPE_OBLIGATOIRE = "obligatoire"
CALENDAR_TYPE_ACADEMIES = "academies"

CALENDAR_TYPES = {
    CALENDAR_TYPE_OBLIGATOIRE: "Cal_Obli",
    CALENDAR_TYPE_ACADEMIES: "Cal_ESAHR",
}

CALENDAR_TYPE_NAMES = {
    CALENDAR_TYPE_OBLIGATOIRE: "Enseignement obligatoire",
    CALENDAR_TYPE_ACADEMIES: "Académies (ESAHR)",
}

CONF_CALENDAR_TYPE = "calendar_type"

DEFAULT_CALENDAR_TYPE = CALENDAR_TYPE_OBLIGATOIRE

# Le calendrier scolaire ne change pas souvent : une actualisation par jour
# suffit largement et évite de solliciter le site inutilement.
UPDATE_INTERVAL = timedelta(hours=12)

ATTRIBUTION = "Données : enseignement.be (Fédération Wallonie-Bruxelles)"
