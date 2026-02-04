from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase


class WeeklyActivityFlowTests(APITestCase):
    maxDiff = None

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

    def test_weekly_activity_list_requires_week_number(self):
        resp = self.client.get(f"/api/v1/goal-calendars/{self.calendar_id}/activities/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("week_number", resp.data)

    def test_weekly_activity_list_filters_by_week(self):
        self.create_activity(metric_type="FREQUENCY", week_number=1, title="Week1", target_frequency=2)
        self.create_activity(metric_type="FREQUENCY", week_number=2, title="Week2", target_frequency=2)
        resp = self.client.get(
            f"/api/v1/goal-calendars/{self.calendar_id}/activities/", {"week_number": 1}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["title"], "Week1")

    def test_list_activity_metric_types(self):
        resp = self.client.get("/api/v1/goal-calendars/activities/metric-types/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("metric_types", resp.data)
        values = {item["value"] for item in resp.data["metric_types"]}
        self.assertTrue({"FREQUENCY", "QUANTITY", "SPECIFIC_DAYS"}.issubset(values))

    def test_frequency_progress_rejects_wrong_metric(self):
        qty_activity = self.create_activity(
            metric_type="QUANTITY", week_number=1, title="Count things", target_quantity=5
        )
        resp = self.client.post(
            f"/api/v1/goal-calendars/{self.calendar_id}/activities/{qty_activity}/progress/frequency/",
            {"day": "monday"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quantity_progress_success_and_validation(self):
        qty_activity = self.create_activity(
            metric_type="QUANTITY", week_number=1, title="Count commits", target_quantity=10
        )
        resp = self.client.post(
            f"/api/v1/goal-calendars/{self.calendar_id}/activities/{qty_activity}/progress/quantity/",
            {"amount": 3},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["quantity_progress"], 3)

        invalid_resp = self.client.post(
            f"/api/v1/goal-calendars/{self.calendar_id}/activities/{qty_activity}/progress/quantity/",
            {"amount": -1},
            format="json",
        )
        self.assertEqual(invalid_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("amount", invalid_resp.data)

    def test_specific_days_progress_success_and_duplicate_check(self):
        specific_activity = self.create_activity(
            metric_type="SPECIFIC_DAYS",
            week_number=1,
            title="Yoga days",
            specific_days=["monday", "wednesday"],
        )
        first = self.client.post(
            f"/api/v1/goal-calendars/{self.calendar_id}/activities/{specific_activity}/progress/specific-days/",
            {"day": "monday"},
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertIn("monday", first.data["completed_days"])

        duplicate = self.client.post(
            f"/api/v1/goal-calendars/{self.calendar_id}/activities/{specific_activity}/progress/specific-days/",
            {"day": "monday"},
            format="json",
        )
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("day", duplicate.data)

        not_configured = self.client.post(
            f"/api/v1/goal-calendars/{self.calendar_id}/activities/{specific_activity}/progress/specific-days/",
            {"day": "friday"},
            format="json",
        )
        self.assertEqual(not_configured.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("day", not_configured.data)

    def test_weekly_report_requires_valid_week_number(self):
        missing = self.client.get(
            f"/api/v1/goal-calendars/{self.calendar_id}/activities/report/",
        )
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)
        invalid = self.client.get(
            f"/api/v1/goal-calendars/{self.calendar_id}/activities/report/", {"week_number": "abc"}
        )
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_access_other_users_calendar(self):
        other_calendar = self.create_calendar_for_other_user()
        resp = self.client.get(
            f"/api/v1/goal-calendars/{other_calendar}/activities/",
            {"week_number": 1},
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # Helpers
    def create_activity(self, metric_type, week_number, title, **extra):
        payload = {
            "title": title,
            "week_number": week_number,
            "metric_type": metric_type,
            "target_frequency": None,
            "target_quantity": None,
            "specific_days": [],
            **extra,
        }
        resp = self.client.post(
            f"/api/v1/goal-calendars/{self.calendar_id}/activities/",
            payload,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        return resp.data["id"]

    def create_calendar_for_other_user(self):
        # remove current auth to register and login as another user
        self.client.credentials()
        other_payload = {
            "username": "charlie",
            "email": "charlie@example.com",
            "password": "StrongPass123!",
            "first_name": "Charlie",
            "last_name": "Tester",
        }
        self.client.post("/api/v1/auth/register/", other_payload, format="json")
        login_resp = self.client.post(
            "/api/v1/auth/login/",
            {"username": "charlie", "password": "StrongPass123!"},
            format="json",
        )
        token = login_resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        start_date = timezone.localdate() + timedelta(days=2)
        resp = self.client.post(
            "/api/v1/goal-calendars/",
            {"title": "Other calendar", "num_weeks": 2, "start_date": start_date},
            format="json",
        )
        calendar_id = resp.data["id"]
        # restore original user auth
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        return calendar_id
