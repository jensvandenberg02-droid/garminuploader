# Loop- en zwemworkouts voor de garminuploader.
# Loop-HR-zones herberekend na Knokke (max HR loop 204, Garmin-zones).
# Zwem-HR-zones apart, o.b.v. zwem-max HR 202 (Garmin zwemzones-scherm).
# Oude Knokke-taperworkouts (augustus, race voorbij) verwijderd om
# per ongeluk herpushen te vermijden.

HR = {
    "recovery": (126, 142),  # Z1 loop
    "easy": (143, 157),      # Z2 loop
    "tempo": (158, 173),     # Z3 loop
    "race": (174, 188),      # Z4 loop
    "hard": (188, 204),      # Z5 loop
}

SWIM_HR = {
    "z1": (115, 130),
    "z2": (130, 145),
    "z3": (145, 160),
    "z4": (160, 175),
    "z5": (175, 202),
}

# Referentietempo's gebruikt voor tijd -> meters omzetting (sept 2026):
#   loop zone 2 (easy): ~5:45 min/km
#   zwem rustig/technisch: ~1:55 min/100m
# Pas deze aan in een volgende ronde zodra je tempo's wijzigen.

RUN_WORKOUTS = [
    ("23/09/2026 - Loop rustig zone 2 (~45min)", "2026-09-23", [
        ("active", 7800, "easy"),
    ]),
    ("26/09/2026 - OPTIONEEL Shakeout loop (~30min, enkel indien fris)", "2026-09-26", [
        ("active", 5200, "recovery"),
    ]),
]

# (naam, datum, totaal_meters, zwemzone voor de hoofdset)
SWIM_WORKOUTS = [
    ("22/09/2026 - Zwem rustig CSS/technisch (~35min)", "2026-09-22", 1800, "z2"),
    ("25/09/2026 - Zwem kort technisch (~25min)", "2026-09-25", 1300, "z2"),
    ("29/09/2026 - Zwem rustig onderhoud (~35min)", "2026-09-29", 1800, "z2"),
]
