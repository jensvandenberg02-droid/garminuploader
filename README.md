# Knokke 70.3 — Garmin workout uploader

Persoonlijk webtooltje: log in met je Garmin-account en upload/plan in één
klik alle 19 loop- en zwemworkouts (laatste 5 weken voor Ironman 70.3 Knokke,
6 september 2026) rechtstreeks naar Garmin Connect.

## Hoe het werkt

- **Frontend**: één simpele pagina (`templates/index.html`) met een
  login-formulier.
- **Backend**: een kleine Flask-server (`app.py`) die met de
  community-library [`garminconnect`](https://github.com/cyberjunky/python-garminconnect)
  inlogt bij Garmin en voor elke workout een gestructureerde sessie
  aanmaakt + inplant op de juiste datum.
- **Workout-data**: staat in `workouts_data.py` (hartslagzones o.b.v.
  Karvonen, CSS-zwemtempo 1:40/100m).

## Lokaal draaien

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 app.py
```

Open daarna **http://127.0.0.1:5000** in je browser, vul je Garmin-login in
en klik op de knop.

## Op GitHub zetten

```bash
git init
git add .
git commit -m "Garmin workout uploader voor Knokke 70.3"
git branch -M main
git remote add origin <jouw-repo-url>
git push -u origin main
```

`.gitignore` sluit al de gevoelige/lokale bestanden uit (zie hieronder) —
er komt niets van je account mee naar GitHub.

## Belangrijk over veiligheid

- **Wachtwoord**: wordt nergens opgeslagen. Het gaat één keer van het
  formulier naar je eigen lokale server, en die geeft het door aan Garmin
  om in te loggen. Daarna wordt de variabele in `app.py` expliciet
  leeggemaakt.
- **Sessie-token**: na de eerste login slaat de `garminconnect`-library een
  vernieuwbaar sessietoken lokaal op in `~/.garminconnect` (niet in deze
  projectmap, dus dat komt sowieso niet mee naar GitHub).
- **Niet publiek hosten**: dit is bewust een 1-persoons-tooltje, geen
  publieke webapp. Zet dit dus **niet** live op een server die voor
  iedereen bereikbaar is zonder extra login/beveiliging ervoor — anders
  kan een derde jouw Garmin-inloggegevens invullen via jouw formulier en zo
  toegang krijgen tot je account. Draai het lokaal, of achter een eigen
  wachtwoord/VPN als je het toch ergens host.
- **Niet-officiële API**: `garminconnect` spreekt Garmin's interne, niet
  publiek gedocumenteerde API aan. Dat werkt op dit moment goed, maar kan
  in theorie ooit breken als Garmin iets wijzigt. Check bij problemen
  https://github.com/cyberjunky/python-garminconnect voor updates.

## Workouts aanpassen

Wijzig `workouts_data.py` — elke loopworkout is een lijst van stappen
`(type, meters, hr_zone)` met type `warmup` / `active` / `recovery` /
`cooldown`, en elke zwemworkout is `(naam, datum, totaal_meters)`.
