# Alle 19 loop- en zwemworkouts (Ironman 70.3 Knokke, laatste 5 weken).
# Zelfde data als de eerder gegenereerde .tcx-bestanden.

HR = {"recovery": (125, 140), "easy": (140, 156), "tempo": (156, 171), "race": (171, 183), "hard": (183, 196)}

RUN_WORKOUTS = [
    ("04/08/2026 - W1 Di - Tempo 8km", "2026-08-04", [
        ("warmup", 2000, "easy"), ("active", 3000, "easy"), ("active", 2500, "race"), ("cooldown", 500, "recovery")]),
    ("06/08/2026 - W1 Do - 8km + strides", "2026-08-06", [
        ("active", 7000, "easy"), ("active", 100, "hard"), ("recovery", 100, "recovery"),
        ("active", 100, "hard"), ("recovery", 100, "recovery"),
        ("active", 100, "hard"), ("recovery", 100, "recovery"),
        ("active", 100, "hard"), ("cooldown", 400, "recovery")]),
    ("10/08/2026 - W2 Ma - Brickloop 5km", "2026-08-10", [
        ("active", 1000, "easy"), ("active", 3500, "easy"), ("cooldown", 500, "recovery")]),
    ("11/08/2026 - W2 Di - Herstel 6km", "2026-08-11", [("active", 6000, "recovery")]),
    ("13/08/2026 - W2 Do - Lange duurloop 14-15km", "2026-08-13", [
        ("warmup", 1500, "easy"), ("active", 12000, "easy"), ("cooldown", 1000, "recovery")]),
    ("18/08/2026 - W3 Di - Racepace intervallen 8km", "2026-08-18", [
        ("warmup", 2000, "easy"), ("active", 1500, "race"), ("recovery", 400, "recovery"),
        ("active", 1500, "race"), ("recovery", 400, "recovery"), ("active", 1200, "race"),
        ("cooldown", 1000, "recovery")]),
    ("20/08/2026 - W3 Do - Rustig 10km", "2026-08-20", [("active", 10000, "easy")]),
    ("22/08/2026 - W3 Za - Brickloop 10km (generale)", "2026-08-22", [
        ("active", 1000, "easy"), ("active", 7000, "race"), ("cooldown", 2000, "easy")]),
    ("25/08/2026 - W4 Di - Kort scherp 6km", "2026-08-25", [
        ("warmup", 1500, "easy"), ("active", 400, "race"), ("recovery", 300, "recovery"),
        ("active", 400, "race"), ("recovery", 300, "recovery"), ("active", 400, "race"),
        ("cooldown", 2700, "easy")]),
    ("27/08/2026 - W4 Do - Rustig 6-8km", "2026-08-27", [("active", 7000, "easy")]),
    ("30/08/2026 - W4 Zo - Brickloop kort 5km", "2026-08-30", [("active", 5000, "easy")]),
    ("01/09/2026 - W5 Di - 4km + strides", "2026-09-01", [
        ("active", 3000, "easy"), ("active", 300, "race"), ("recovery", 200, "recovery"),
        ("active", 300, "race"), ("cooldown", 200, "recovery")]),
    ("04/09/2026 - W5 Vr - Activatie 10min", "2026-09-04", [
        ("active", 1200, "easy"), ("active", 300, "race"), ("cooldown", 500, "recovery")]),
]

# (naam, datum, totaal_meters)
SWIM_WORKOUTS = [
    ("05/08/2026 - W1 Wo - CSS 2500m", "2026-08-05", 2500),
    ("12/08/2026 - W2 Wo - CSS 3000m + open water", "2026-08-12", 3000),
    ("19/08/2026 - W3 Wo - CSS 2500m + 2x750m racepace", "2026-08-19", 2500),
    ("26/08/2026 - W4 Wo - Rustig 2000m + tempo", "2026-08-26", 2000),
    ("31/08/2026 - W5 Ma - Technique 1000m", "2026-08-31", 1000),
    ("02/09/2026 - W5 Wo - Technique 1000m", "2026-09-02", 1000),
]
