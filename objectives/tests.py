from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from django.contrib.auth import get_user_model


User = get_user_model()


class ObjectiveFlowTests(APITestCase):
    def setUp(self):
        self.register_user()
        self.verify_email("bob@example.com")
        self.authenticate()
        self.calendar_id = self.create_calendar()

    def register_user(self):
        payload = {
            "username": "bob",
            "email": "bob@example.com",
            "password": "StrongPass123!",
            "first_name": "Bob",
            "last_name": "Builder",
        }
        resp = self.client.post("/api/v1/auth/register/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def verify_email(self, email):
        user = User.objects.get(email=email)
        user.email_verified = True
        user.email_verification_code_hash = None
        user.email_verification_expires_at = None
        user.save(update_fields=["email_verified", "email_verification_code_hash", "email_verification_expires_at"])

    def authenticate(self):
        resp = self.client.post(
            "/api/v1/auth/login/",
            {"username": "bob", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        token = resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def create_calendar(self):
        start_date = timezone.localdate() + timedelta(days=1)
        payload = {"title": "Roadmap", "num_weeks": 6, "start_date": start_date}
        resp = self.client.post("/api/v1/goal-calendars/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        return resp.data["id"]

    def test_create_and_complete_objective(self):
        # Cria um objetivo atrelado a calendario
        create_payload = {
            "objective_type": "GOAL_CALENDAR",
            "goal_calendar": self.calendar_id,
            "title": "Sprint week 1",
            "description": "Entregar backlog da semana",
        }
        create_resp = self.client.post("/api/v1/objectives/", create_payload, format="json")
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        objective_id = create_resp.data["id"]

        # Lista por tipo
        list_resp = self.client.get("/api/v1/objectives/type/GOAL_CALENDAR/")
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(any(obj["id"] == objective_id for obj in list_resp.data))

        # Marca como concluido
        complete_resp = self.client.post(f"/api/v1/objectives/{objective_id}/complete/")
        self.assertEqual(complete_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(complete_resp.data["is_complete"])

    def test_list_objective_types(self):
        resp = self.client.get("/api/v1/objectives/types/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("objective_types", resp.data)
        values = {item["value"] for item in resp.data["objective_types"]}
        self.assertTrue({"LONG_TERM", "MEDIUM_TERM", "GOAL_CALENDAR"}.issubset(values))
