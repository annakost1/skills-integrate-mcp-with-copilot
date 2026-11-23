import json
import tempfile
import unittest
from http.cookies import SimpleCookie
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, Request, Response

from src import app as app_module


def make_request(cookie: str = "") -> Request:
    headers = [(b"cookie", cookie.encode("ascii"))] if cookie else []
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": headers,
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "root_path": "",
        }
    )


class TeacherAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        app_module._teacher_sessions.clear()

    def test_password_hash_is_salted_and_verified(self) -> None:
        first_hash = app_module.hash_password("correct horse battery staple")
        second_hash = app_module.hash_password("correct horse battery staple")

        self.assertNotEqual(first_hash, second_hash)
        self.assertTrue(app_module.verify_password("correct horse battery staple", first_hash))
        self.assertFalse(app_module.verify_password("wrong password", first_hash))
        self.assertFalse(app_module.verify_password("password", "invalid-hash"))

    def test_login_issues_teacher_session_cookie(self) -> None:
        password_hash = app_module.hash_password("teacher-password")
        with tempfile.TemporaryDirectory() as directory:
            credentials_path = Path(directory) / "teachers.json"
            credentials_path.write_text(
                json.dumps({"teachers": {"teacher": password_hash}}),
                encoding="utf-8",
            )
            response = Response()
            with patch.dict(
                "os.environ", {"TEACHER_CREDENTIALS_FILE": str(credentials_path)}
            ):
                result = app_module.login(
                    app_module.TeacherLogin(
                        username="teacher", password="teacher-password"
                    ),
                    response,
                )

        self.assertEqual(result, {"authenticated": True, "username": "teacher"})
        cookie = SimpleCookie()
        cookie.load(response.headers["set-cookie"])
        session_id = cookie[app_module.SESSION_COOKIE].value
        request = make_request(f"{app_module.SESSION_COOKIE}={session_id}")
        self.assertEqual(app_module.get_current_teacher(request), "teacher")
        self.assertTrue(cookie[app_module.SESSION_COOKIE]["httponly"])

    def test_registration_routes_require_teacher_authentication(self) -> None:
        protected_routes = {
            route.path: route
            for route in app_module.app.routes
            if route.path
            in {
                "/activities/{activity_name}/signup",
                "/activities/{activity_name}/unregister",
            }
        }

        self.assertEqual(len(protected_routes), 2)
        for route in protected_routes.values():
            dependency_calls = {dependency.call for dependency in route.dependant.dependencies}
            self.assertIn(app_module.get_current_teacher, dependency_calls)

    def test_missing_session_is_rejected(self) -> None:
        with self.assertRaises(HTTPException) as error:
            app_module.get_current_teacher(make_request())

        self.assertEqual(error.exception.status_code, 401)

    def test_expired_session_is_rejected_and_removed(self) -> None:
        session_id = "expired-session"
        app_module._teacher_sessions[session_id] = ("teacher", 0)

        with self.assertRaises(HTTPException) as error:
            app_module.get_current_teacher(
                make_request(f"{app_module.SESSION_COOKIE}={session_id}")
            )

        self.assertEqual(error.exception.status_code, 401)
        self.assertNotIn(session_id, app_module._teacher_sessions)


if __name__ == "__main__":
    unittest.main()
