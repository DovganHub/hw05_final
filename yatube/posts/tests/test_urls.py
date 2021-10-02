from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from ..models import Group, Post
from django.urls import reverse

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=User.objects.create_user(username='real_author'),
            text='Длина сообщения более 15 символов',
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(StaticURLTests.user)

    def test_homepage(self):
        response = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(response.status_code, 200)

    def test_task_post_edit_url_redirect_nonauthor_on_post_details(self):
        """Страница по адресу /posts/<post_id>/edit перенаправит неавтора
         на страницу поста.
        """
        response = self.authorized_client.get(reverse('posts:post_edit',
                                              kwargs={'post_id':
                                                      StaticURLTests.post.pk}))
        self.assertRedirects(
            response, reverse('posts:post_detail',
                              kwargs={'post_id': StaticURLTests.post.pk})
        )

    def test_task_create_url_redirect_unauthorized_on_post_details(self):
        """Страница по адресу /posts/<post_id>/edit перенаправит неавтора
         на страницу поста.
        """
        response = self.guest_client.get(reverse('posts:post_create'))
        self.assertRedirects(
            response, reverse('users:login')
        )

    def test_urls_uses_correct_template_authorized(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/group_list.html': reverse('posts:group',
                                             kwargs={'slug':
                                                     StaticURLTests.group.slug}
                                             ),
            'posts/profile.html': reverse('posts:profile',
                                          kwargs={'username':
                                                  StaticURLTests.user.username}
                                          ),
            'posts/post_detail.html': reverse('posts:post_detail',
                                              kwargs={'post_id':
                                                      StaticURLTests.post.pk}),
            'posts/create_post.html': reverse('posts:post_create'),
        }
        for template, adress in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertTemplateUsed(response, template)

    def test_task_detail_url_exists_at_desired_location_authorized(self):
        """Страница unexisting_page/ вернет 404 как авторизованному, так и
        неавторизованному пользоватетелю"""
        response = self.guest_client.get('unexisting_page/')
        self.assertEqual(response.status_code, 404)
        response = self.authorized_client.get('unexisting_page/')
        self.assertEqual(response.status_code, 404)
