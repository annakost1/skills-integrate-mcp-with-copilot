# Mergington High School Activities API

A FastAPI application for viewing extracurricular activities and managing student registrations.

## Features

- View all available extracurricular activities
- Teacher sign-in for registering and unregistering students
- Public activity and participant listings

## Getting Started

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Create the local credentials file:

   ```
   cp src/teachers.example.json src/teachers.json
   python src/manage_teachers.py teacher-username
   ```

   The command prompts for the password and stores only a salted scrypt hash. The local
   `src/teachers.json` file is ignored by Git. Do not commit credentials.

3. Start the application from the repository root:

   ```
   uvicorn src.app:app --reload
   ```

4. Open http://localhost:8000.

Set `COOKIE_SECURE=true` when serving the application over HTTPS. Teacher sessions are
stored in memory and expire after eight hours; restarting the server logs everyone out.

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Public list of activities and participants                          |
| GET    | `/auth/session`                                                   | Check whether the current browser has a teacher session              |
| POST   | `/auth/login`                                                     | Sign in with a teacher username and password                         |
| POST   | `/auth/logout`                                                    | End the current teacher session                                      |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Teacher-only student registration                                    |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Teacher-only student removal                                    |

Registration and removal require the HttpOnly teacher session cookie set by `/auth/login`.
Activity and participant listings remain publicly readable.
