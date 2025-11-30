from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase


@override_settings(DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}})
class WeeklyActivityFlowTests(APITestCase):
    def setUp(self):
        self.register_user()
        self.authenticate()
        self.calendar_id = self.create_calendar()

    def register_user(self):
        payload = {
            "username": "alice",
            "email": "alice@example.com",
            "password": "StrongPass123!",
            "first_name": "Alice",
            "last_name": "Tester",
        }
        resp = self.client.post("/api/v1/auth/register/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def authenticate(self):
        resp = self.client.post(
            "/api/v1/auth/login/",
            {"username": "alice", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.access = resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def create_calendar(self):
        start_date = timezone.localdate() + timedelta(days=1)
        payload = {"title": "Q1 Plan", "num_weeks": 4, "start_date": start_date}
        resp = self.client.post("/api/v1/goal-calendars/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        return resp.data["id"]

    def test_weekly_activity_progress_and_report(self):
        activity_payload = {
            "title": "Gym",
            "description": "3x per week",
            "week_number": 1,
            "metric_type": "FREQUENCY",
            "target_frequency": 3,
        }
        resp = self.client.post(
            f"/api/v1/goal-calendars/{self.calendar_id}/activities/",
            activity_payload,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        activity_id = resp.data["id"]

        progress_resp = self.client.post(
            f"/api/v1/goal-calendars/{self.calendar_id}/activities/{activity_id}/progress/frequency/",
            {"day": "monday"},
            format="json",
        )
        self.assertEqual(progress_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(progress_resp.data["frequency_progress"], 1)
        self.assertIn("monday", progress_resp.data["completed_days"])

        report_resp = self.client.get(
            f"/api/v1/goal-calendars/{self.calendar_id}/activities/report/",
            {"week_number": 1},
        )
        self.assertEqual(report_resp.status_code, status.HTTP_200_OK)
        self.assertIn("progress", report_resp.data)
        self.assertTrue(report_resp.data["progress"])
        self.assertGreaterEqual(report_resp.data["general_progress"], 0)
