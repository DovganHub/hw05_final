from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from ..models import Group, Post

User = get_user_model()


class TaskPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        Post.objects.bulk_create([Post(author=cls.user,
                                 text='Проверка паджинатора',
                                 group=cls.group) for i in range(13)])

    def setUp(self):
        self.guest_client = Client()

    def test_first_page_contains_ten_records(self):
        """На первой странице 10 объектов"""
        url_names = [
            reverse('posts:index'),
            reverse('posts:group', kwargs={'slug': TaskPagesTests.group.slug}),
            reverse('posts:profile',
                    kwargs={'username': TaskPagesTests.user.username})
        ]
        for url in url_names:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_records(self):
        """На второй странице 3 объекта"""
        url_names = [
            reverse('posts:index'),
            reverse('posts:group',
                    kwargs={'slug': TaskPagesTests.group.slug}),
            reverse('posts:profile',
                    kwargs={'username':
                            TaskPagesTests.user.username})
        ]
        for url in url_names:
            with self.subTest(url=url):
                response = self.guest_client.get(url + '?page=2')
                self.assertEqual(len(response.context['page_obj']), 3)
