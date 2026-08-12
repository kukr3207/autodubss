from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class FuturesExecutionTests(TestCase):
    def setUp(self):
        self.url = reverse("execute_bn_futures_bot")
        self.staff_user = User.objects.create_user(
            "operator", password="password", is_staff=True
        )

    def test_execution_requires_staff_authentication(self):
        response = self.client.post(self.url)

        self.assertRedirects(
            response,
            f"{reverse('admin:login')}?next={self.url}",
            fetch_redirect_response=False,
        )

    def test_execution_only_accepts_posts(self):
        self.client.force_login(self.staff_user)

        self.assertEqual(self.client.get(self.url).status_code, 405)

    @patch("bn_futures.views._run_futures_order")
    def test_staff_can_run_the_futures_order(self, run_order):
        self.client.force_login(self.staff_user)

        response = self.client.post(self.url, follow=True)

        run_order.assert_called_once_with()
        self.assertContains(response, "futures bot completed")

    @patch("bn_futures.views._run_futures_order", side_effect=RuntimeError("broker"))
    def test_execution_failure_is_reported_without_crashing(self, run_order):
        self.client.force_login(self.staff_user)

        response = self.client.post(self.url, follow=True)

        run_order.assert_called_once_with()
        self.assertContains(response, "could not be executed")
