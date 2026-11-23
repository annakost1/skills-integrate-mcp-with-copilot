"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School. Teachers manage
student registrations.
"""

import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

SESSION_COOKIE = "teacher_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
_teacher_sessions: dict[str, tuple[str, float]] = {}


class TeacherLogin(BaseModel):
    username: str
    password: str


def hash_password(password: str) -> str:
    """Return a salted scrypt hash suitable for the local teacher credentials file."""
    salt = secrets.token_bytes(16)
    password_hash = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32
    )
    return f"scrypt${salt.hex()}${password_hash.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against the stored scrypt hash."""
    try:
        algorithm, salt_hex, hash_hex = stored_hash.split("$")
        if algorithm != "scrypt":
            return False
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        actual_hash = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32
        )
    except (AttributeError, ValueError):
        return False
    return hmac.compare_digest(actual_hash, expected_hash)


def load_teacher_credentials() -> dict[str, str]:
    credentials_path = Path(
        os.environ.get("TEACHER_CREDENTIALS_FILE", current_dir / "teachers.json")
    )
    try:
        with credentials_path.open(encoding="utf-8") as credentials_file:
            data = json.load(credentials_file)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=503,
            detail="Teacher credentials are not configured correctly",
        ) from error

    teachers = data.get("teachers") if isinstance(data, dict) else None
    if not isinstance(teachers, dict) or not all(
        isinstance(username, str) and isinstance(password_hash, str)
        for username, password_hash in teachers.items()
    ):
        raise HTTPException(
            status_code=503,
            detail="Teacher credentials are not configured correctly",
        )
    return teachers


def get_current_teacher(request: Request) -> str:
    session_id = request.cookies.get(SESSION_COOKIE)
    session = _teacher_sessions.get(session_id) if session_id else None
    if session is None:
        raise HTTPException(status_code=401, detail="Teacher login required")

    username, expires_at = session
    if expires_at <= time.time():
        _teacher_sessions.pop(session_id, None)
        raise HTTPException(status_code=401, detail="Teacher session has expired")
    return username


@app.post("/auth/login")
def login(credentials: TeacherLogin, response: Response):
    stored_hash = load_teacher_credentials().get(credentials.username)
    if stored_hash is None or not verify_password(credentials.password, stored_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    session_id = secrets.token_urlsafe(32)
    _teacher_sessions[session_id] = (
        credentials.username,
        time.time() + SESSION_TTL_SECONDS,
    )
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=os.environ.get("COOKIE_SECURE", "").lower() == "true",
        samesite="strict",
        path="/",
    )
    return {"authenticated": True, "username": credentials.username}


@app.post("/auth/logout")
def logout(request: Request, response: Response):
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        _teacher_sessions.pop(session_id, None)
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=os.environ.get("COOKIE_SECURE", "").lower() == "true",
        samesite="strict",
        path="/",
    )
    return {"authenticated": False}


@app.get("/auth/session")
def get_session(request: Request):
    try:
        username = get_current_teacher(request)
    except HTTPException as error:
        if error.status_code != 401:
            raise
        return {"authenticated": False}
    return {"authenticated": True, "username": username}


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post(
    "/activities/{activity_name}/signup",
    dependencies=[Depends(get_current_teacher)],
)
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete(
    "/activities/{activity_name}/unregister",
    dependencies=[Depends(get_current_teacher)],
)
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
