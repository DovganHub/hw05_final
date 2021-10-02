from django.test import Client, TestCase
from django.urls import reverse


class StaticURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_aboutapp_urls_use_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            'about/tech.html': reverse('about:tech'),
            'about/author.html': reverse('about:author'),
        }
        for template, url in templates_url_names.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_aboutapp_urls_availability(self):
        """URL-адрес доступен."""
        url_names = [
            reverse('about:tech'),
            reverse('about:author'),
        ]

        for url in url_names:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, 200)
