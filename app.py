"""
Kleine persoonlijke website: log in met je eigen Garmin-account en upload/plan
in één klik alle 19 loop- en zwemworkouts naar Garmin Connect.

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
  zonder extra beveiliging (dit is bewust een 1-persoons-toolt je, geen
  publieke webapp) — anders kan iemand anders jouw Garmin-inloggegevens
  onderscheppen.
"""

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

from workouts_data import HR, RUN_WORKOUTS, SWIM_WORKOUTS

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


def build_run_steps(step_defs):
    steps = []
    for i, (kind, meters, zone) in enumerate(step_defs, start=1):
        low, high = HR[zone]
        steps.append(make_distance_step(i, kind, meters, low, high))
    return steps


@app.route("/")
@require_site_login
def index():
    return render_template("index.html",
                            run_count=len(RUN_WORKOUTS),
                            swim_count=len(SWIM_WORKOUTS))


@app.route("/upload", methods=["POST"])
@require_site_login
def upload():
    email = request.form.get("email")
    password = request.form.get("password")
    mfa_code = request.form.get("mfa_code") or None

    if not email or not password:
        return jsonify({"error": "E-mail en wachtwoord zijn verplicht."}), 400

    log = []
    try:
        client = Garmin(email, password, prompt_mfa=lambda: mfa_code or "")
        client.login("~/.garminconnect")
    except Exception as e:
        return jsonify({"error": f"Inloggen bij Garmin mislukt: {e}"}), 401
    finally:
        # wachtwoord expliciet uit het geheugen halen, we hebben het niet meer nodig
        password = None

    # 13 loopworkouts
    for name, date_str, step_defs in RUN_WORKOUTS:
        try:
            workout = RunningWorkout(
                workoutName=name,
                estimatedDurationInSecs=0,
                workoutSegments=[WorkoutSegment(segmentOrder=1, sportType=RUN_SPORT,
                                                 workoutSteps=build_run_steps(step_defs))],
            )
            result = client.upload_running_workout(workout)
            workout_id = result.get("workoutId") or result.get("workoutSummary", {}).get("workoutId")
            if workout_id:
                client.schedule_workout(workout_id, date_str)
            log.append({"name": name, "date": date_str, "status": "ok"})
        except Exception as e:
            log.append({"name": name, "date": date_str, "status": f"fout: {e}"})

    # 6 zwemworkouts
    for name, date_str, meters in SWIM_WORKOUTS:
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
