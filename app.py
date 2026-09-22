"""
Kleine persoonlijke website: log in met je eigen Garmin-account en upload/plan
in één klik al je loop- en zwemworkouts naar Garmin Connect.

Je kan ofwel de standaard workouts uit workouts_data.py gebruiken, ofwel je
eigen workout-plan als JSON-bestand uploaden op de site zelf (zie
WORKOUTS_JSON_VOORBEELD hieronder voor het formaat). Zo hoef je niet telkens
de code aan te passen en opnieuw te deployen op Render als je een nieuw
trainingsblok hebt.

Draai lokaal:
    pip install -r requirements.txt
    python3 app.py
Open dan http://127.0.0.1:5000 in je browser.

BELANGRIJK:
- Dit gebruikt de niet-officiële, community-onderhouden library `garminconnect`
  (https://github.com/cyberjunky/python-garminconnect), die Garmin's interne
  (niet publiek gedocumenteerde) API aanspreekt. Dat kan ooit breken als
  Garmin iets wijzigt aan hun backend.
- Je Garmin-wachtwoord wordt NERGENS opgeslagen door deze app. Het staat één
  keer, kortstondig, in het geheugen van het serverproces tijdens het
  inloggen, en wordt daarna weggegooid. Alleen het sessie-token (niet je
  wachtwoord) wordt lokaal gecachet in ~/.garminconnect zodat je niet elke
  keer opnieuw hoeft in te loggen.
- Draai dit ALLEEN lokaal op je eigen machine (of eventueel op een privé
  server die alleen jij kan bereiken). Zet dit nooit online toegankelijk
  zonder extra beveiliging (dit is bewust een 1-persoons-tooltje, geen
  publieke webapp) — anders kan iemand anders jouw Garmin-inloggegevens
  onderscheppen.

WORKOUTS_JSON_VOORBEELD (dit is het formaat dat je kan uploaden i.p.v. de
hardcoded workouts_data.py te gebruiken):
{
  "hr_zones": {
    "recovery": [125, 140],
    "easy": [140, 156],
    "tempo": [156, 171],
    "race": [171, 183],
    "hard": [183, 196]
  },
  "run_workouts": [
    {
      "name": "04/08/2026 - W1 Di - Tempo 8km",
      "date": "2026-08-04",
      "steps": [
        ["warmup", 2000, "easy"],
        ["active", 3000, "easy"],
        ["active", 2500, "race"],
        ["cooldown", 500, "recovery"]
      ]
    }
  ],
  "swim_workouts": [
    {
      "name": "05/08/2026 - W1 Wo - CSS 2500m",
      "date": "2026-08-05",
      "meters": 2500
    }
  ]
}
Elke "step" is [kind, meters, zone] waarbij kind een van
"warmup" / "active" / "recovery" / "cooldown" is, en zone een sleutel uit
"hr_zones" hierboven.
"""

import json
import os
from functools import wraps
from flask import Flask, render_template, request, jsonify, Response
from garminconnect import Garmin
from garminconnect.workout import (
    RunningWorkout,
    SwimmingWorkout,
    WorkoutSegment,
    ExecutableStep,
    StepType,
    ConditionType,
    TargetType,
)

from workouts_data import HR as DEFAULT_HR, RUN_WORKOUTS as DEFAULT_RUN_WORKOUTS, SWIM_WORKOUTS as DEFAULT_SWIM_WORKOUTS

app = Flask(__name__)

# ---------- Site-toegangsbeveiliging (los van je Garmin-login) ----------
# Zet SITE_USERNAME en SITE_PASSWORD als environment variables in je hosting
# platform (bv. Render). Zonder deze twee env vars werkt de site alleen nog
# lokaal, zonder wachtwoordslot (handig tijdens lokaal testen).
SITE_USERNAME = os.environ.get("SITE_USERNAME")
SITE_PASSWORD = os.environ.get("SITE_PASSWORD")


def check_site_auth(auth):
    if not SITE_USERNAME or not SITE_PASSWORD:
        return True  # geen beveiliging ingesteld (lokaal testen)
    return auth and auth.username == SITE_USERNAME and auth.password == SITE_PASSWORD


def require_site_login(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if not check_site_auth(auth):
            return Response(
                "Login vereist.", 401,
                {"WWW-Authenticate": 'Basic realm="Login Required"'},
            )
        return f(*args, **kwargs)
    return wrapper


RUN_SPORT = {"sportTypeId": 1, "sportTypeKey": "running"}
SWIM_SPORT = {"sportTypeId": 4, "sportTypeKey": "swimming"}

STEP_TYPE_IDS = {
    "warmup": (StepType.WARMUP, "warmup"),
    "active": (StepType.INTERVAL, "interval"),
    "recovery": (StepType.RECOVERY, "recovery"),
    "cooldown": (StepType.COOLDOWN, "cooldown"),
}


def make_distance_step(step_order, kind, meters, low=None, high=None):
    """Bouwt een stap die eindigt op afstand (meters), optioneel met een
    hartslagzone (low/high in bpm) als target."""
    type_id, type_key = STEP_TYPE_IDS[kind]
    if low is not None and high is not None:
        target_type = {
            "workoutTargetTypeId": TargetType.HEART_RATE_ZONE,
            "workoutTargetTypeKey": "heart.rate.zone",
            "displayOrder": 4,
        }
    else:
        target_type = {
            "workoutTargetTypeId": TargetType.NO_TARGET,
            "workoutTargetTypeKey": "no.target",
            "displayOrder": 1,
        }
    return ExecutableStep(
        stepOrder=step_order,
        stepType={"stepTypeId": type_id, "stepTypeKey": type_key, "displayOrder": 1},
        endCondition={
            "conditionTypeId": ConditionType.DISTANCE,
            "conditionTypeKey": "distance",
            "displayOrder": 3,
            "displayable": True,
        },
        endConditionValue=float(meters),
        targetType=target_type,
        targetValueOne=low,
        targetValueTwo=high,
    )


def build_run_steps(step_defs, hr_zones):
    steps = []
    for i, (kind, meters, zone) in enumerate(step_defs, start=1):
        low, high = hr_zones[zone]
        steps.append(make_distance_step(i, kind, meters, low, high))
    return steps


def load_plan_from_json(file_storage):
    """Leest een geüpload JSON-bestand in en zet het om naar dezelfde vorm
    als de hardcoded data in workouts_data.py: (hr_zones, run_workouts,
    swim_workouts)."""
    raw = file_storage.read()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(f"ongeldig JSON-bestand ({e})")

    hr_zones = {k: tuple(v) for k, v in data.get("hr_zones", {}).items()} or DEFAULT_HR

    run_workouts = []
    for w in data.get("run_workouts", []):
        steps = [tuple(step) for step in w["steps"]]
        run_workouts.append((w["name"], w["date"], steps))

    swim_workouts = []
    for w in data.get("swim_workouts", []):
        swim_workouts.append((w["name"], w["date"], int(w["meters"])))

    if not run_workouts and not swim_workouts:
        raise ValueError("geen run_workouts of swim_workouts gevonden in het bestand")

    return hr_zones, run_workouts, swim_workouts


@app.route("/")
@require_site_login
def index():
    return render_template("index.html",
                            run_count=len(DEFAULT_RUN_WORKOUTS),
                            swim_count=len(DEFAULT_SWIM_WORKOUTS))


@app.route("/upload", methods=["POST"])
@require_site_login
def upload():
    email = request.form.get("email")
    password = request.form.get("password")
    mfa_code = request.form.get("mfa_code") or None

    if not email or not password:
        return jsonify({"error": "E-mail en wachtwoord zijn verplicht."}), 400

    # Eigen plan geüpload? Gebruik dat. Anders: val terug op workouts_data.py
    plan_file = request.files.get("workouts_file")
    if plan_file and plan_file.filename:
        try:
            hr_zones, run_workouts, swim_workouts = load_plan_from_json(plan_file)
        except Exception as e:
            return jsonify({"error": f"Kon geüpload workouts-bestand niet verwerken: {e}"}), 400
    else:
        hr_zones, run_workouts, swim_workouts = DEFAULT_HR, DEFAULT_RUN_WORKOUTS, DEFAULT_SWIM_WORKOUTS

    log = []
    try:
        client = Garmin(email, password, prompt_mfa=lambda: mfa_code or "")
        client.login("~/.garminconnect")
    except Exception as e:
        return jsonify({"error": f"Inloggen bij Garmin mislukt: {e}"}), 401
    finally:
        # wachtwoord expliciet uit het geheugen halen, we hebben het niet meer nodig
        password = None

    for name, date_str, step_defs in run_workouts:
        try:
            workout = RunningWorkout(
                workoutName=name,
                estimatedDurationInSecs=0,
                workoutSegments=[WorkoutSegment(segmentOrder=1, sportType=RUN_SPORT,
                                                 workoutSteps=build_run_steps(step_defs, hr_zones))],
            )
            result = client.upload_running_workout(workout)
            workout_id = result.get("workoutId") or result.get("workoutSummary", {}).get("workoutId")
            if workout_id:
                client.schedule_workout(workout_id, date_str)
            log.append({"name": name, "date": date_str, "status": "ok"})
        except Exception as e:
            log.append({"name": name, "date": date_str, "status": f"fout: {e}"})

    for name, date_str, meters in swim_workouts:
        try:
            steps = [
                make_distance_step(1, "warmup", 400),
                make_distance_step(2, "active", meters - 400),
                make_distance_step(3, "cooldown", 200),
            ]
            workout = SwimmingWorkout(
                workoutName=name,
                estimatedDurationInSecs=0,
                workoutSegments=[WorkoutSegment(segmentOrder=1, sportType=SWIM_SPORT, workoutSteps=steps)],
            )
            result = client.upload_swimming_workout(workout)
            workout_id = result.get("workoutId") or result.get("workoutSummary", {}).get("workoutId")
            if workout_id:
                client.schedule_workout(workout_id, date_str)
            log.append({"name": name, "date": date_str, "status": "ok"})
        except Exception as e:
            log.append({"name": name, "date": date_str, "status": f"fout: {e}"})

    return jsonify({"results": log})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
