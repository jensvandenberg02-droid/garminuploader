"""
Kleine persoonlijke website: log in met je eigen Garmin-account, upload een
workouts.json-bestand, en plan in één klik alle loop- en zwemworkouts naar
Garmin Connect.

Draai lokaal:
    pip install -r requirements.txt
    python3 app.py
Open dan http://127.0.0.1:5000 in je browser.

WORKOUTS.JSON FORMAAT:
{
  "run_hr_zones":  {"recovery": [126, 142], "easy": [143, 157], "tempo": [158, 173],
                     "race": [174, 188], "hard": [188, 204]},
  "swim_hr_zones": {"z1": [115, 130], "z2": [130, 145], "z3": [145, 160],
                     "z4": [160, 175], "z5": [175, 202]},
  "run_workouts": [
    {"name": "23/09/2026 - Loop rustig zone 2", "date": "2026-09-23",
     "steps": [{"kind": "active", "meters": 7800, "zone": "easy"}]}
  ],
  "swim_workouts": [
    {"name": "22/09/2026 - Zwem rustig", "date": "2026-09-22",
     "meters": 1800, "zone": "z2"}
  ]
}
Elke maand genereer je gewoon een nieuw workouts.json en upload je dat hier —
er hoeft niets meer aangepast te worden aan deze code of op GitHub/Render.

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


def build_run_steps(step_defs, run_hr_zones):
    steps = []
    for i, step in enumerate(step_defs, start=1):
        zone = step.get("zone")
        low, high = (None, None)
        if zone:
            low, high = run_hr_zones[zone]
        steps.append(make_distance_step(i, step["kind"], step["meters"], low, high))
    return steps


@app.route("/")
@require_site_login
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
@require_site_login
def upload():
    email = request.form.get("email")
    password = request.form.get("password")
    mfa_code = request.form.get("mfa_code") or None
    workouts_file = request.files.get("workouts_file")

    if not email or not password:
        return jsonify({"error": "E-mail en wachtwoord zijn verplicht."}), 400
    if not workouts_file:
        return jsonify({"error": "Geen workouts.json geüpload."}), 400

    try:
        data = json.load(workouts_file.stream)
    except Exception as e:
        return jsonify({"error": f"Kon workouts.json niet lezen: {e}"}), 400

    run_hr_zones = data.get("run_hr_zones", {})
    swim_hr_zones = data.get("swim_hr_zones", {})
    run_workouts = data.get("run_workouts", [])
    swim_workouts = data.get("swim_workouts", [])

    log = []
    try:
        client = Garmin(email, password, prompt_mfa=lambda: mfa_code or "")
        client.login("~/.garminconnect")
    except Exception as e:
        return jsonify({"error": f"Inloggen bij Garmin mislukt: {e}"}), 401
    finally:
        # wachtwoord expliciet uit het geheugen halen, we hebben het niet meer nodig
        password = None

    # loopworkouts
    for w in run_workouts:
        name = w.get("name", "Naamloze loopworkout")
        date_str = w.get("date")
        try:
            workout = RunningWorkout(
                workoutName=name,
                estimatedDurationInSecs=0,
                workoutSegments=[WorkoutSegment(segmentOrder=1, sportType=RUN_SPORT,
                                                 workoutSteps=build_run_steps(w["steps"], run_hr_zones))],
            )
            result = client.upload_running_workout(workout)
            workout_id = result.get("workoutId") or result.get("workoutSummary", {}).get("workoutId")
            if workout_id and date_str:
                client.schedule_workout(workout_id, date_str)
            log.append({"name": name, "date": date_str, "status": "ok"})
        except Exception as e:
            log.append({"name": name, "date": date_str, "status": f"fout: {e}"})

    # zwemworkouts
    for w in swim_workouts:
        name = w.get("name", "Naamloze zwemworkout")
        date_str = w.get("date")
        try:
            meters = w["meters"]
            zone = w.get("zone")
            if zone and zone in swim_hr_zones:
                wu_low, wu_high = swim_hr_zones["z1"] if "z1" in swim_hr_zones else (None, None)
                active_low, active_high = swim_hr_zones[zone]
                cd_low, cd_high = swim_hr_zones["z1"] if "z1" in swim_hr_zones else (None, None)
            else:
                wu_low = wu_high = active_low = active_high = cd_low = cd_high = None
            steps = [
                make_distance_step(1, "warmup", 400, wu_low, wu_high),
                make_distance_step(2, "active", meters - 400, active_low, active_high),
                make_distance_step(3, "cooldown", 200, cd_low, cd_high),
            ]
            workout = SwimmingWorkout(
                workoutName=name,
                estimatedDurationInSecs=0,
                workoutSegments=[WorkoutSegment(segmentOrder=1, sportType=SWIM_SPORT, workoutSteps=steps)],
            )
            result = client.upload_swimming_workout(workout)
            workout_id = result.get("workoutId") or result.get("workoutSummary", {}).get("workoutId")
            if workout_id and date_str:
                client.schedule_workout(workout_id, date_str)
            log.append({"name": name, "date": date_str, "status": "ok"})
        except Exception as e:
            log.append({"name": name, "date": date_str, "status": f"fout: {e}"})

    return jsonify({"results": log})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
