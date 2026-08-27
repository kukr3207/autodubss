from django.conf import settings
from django.test import SimpleTestCase
from django.urls import resolve, reverse


class ProjectSmokeTests(SimpleTestCase):
    def test_root_url_resolves_to_the_dashboard(self):
        self.assertEqual(reverse("home"), "/")
        self.assertEqual(resolve("/").url_name, "home")

    def test_local_configuration_has_a_database_and_login_route(self):
        self.assertIn("default", settings.DATABASES)
        self.assertEqual(reverse("login"), "/accounts/login/")
