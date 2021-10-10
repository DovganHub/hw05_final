from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from ..models import Group, Post, Follow
from django import forms
from django.core.cache import cache

User = get_user_model()


class ViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.authoruser = User.objects.create_user(username='author')
        cls.notauthoruser = User.objects.create_user(username='notauthor')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.new_image = SimpleUploadedFile(
            name='new_image.png',
            content=small_gif,
            content_type='image/gif',
        )
        cls.post = Post.objects.create(
            author=cls.authoruser,
            group=cls.group,
            text='Длина сообщения более 15 символов',
            image=cls.new_image,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(ViewsTest.authoruser)
        self.not_follower_client = Client()
        self.not_follower_client.force_login(ViewsTest.notauthoruser)

    def check_posts_context(self, post):
        """Проверяет возвращаемый контекст"""
        self.assertEqual(post.text, ViewsTest.post.text)
        self.assertEqual(post.author, ViewsTest.post.author)
        self.assertEqual(post.group, ViewsTest.post.group)
        self.assertEqual(post.image, ViewsTest.post.image)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group',
                    kwargs={'slug':
                            ViewsTest.group.slug}): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username':
                            ViewsTest.authoruser.username}
                    ): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': ViewsTest.post.pk}
                    ): 'posts/post_detail.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': ViewsTest.post.pk}
                    ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_posts_create_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_posts_edit_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_edit',
                                              kwargs={'post_id':
                                                      ViewsTest.post.pk}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_group_list_show_correct_context(self):
        """Из вью group_list передается правильный контекст."""
        response = self.authorized_client.get(reverse('posts:group',
                                              kwargs={'slug':
                                                      ViewsTest.group.slug
                                                      })
                                              )
        self.check_posts_context(response.context['page_obj'][0])
        self.assertEqual(response.context['group'],
                         ViewsTest.post.group)

    def test_profile_show_correct_context(self):
        """Из вью profile передается правильный контекст."""
        response = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': ViewsTest.authoruser.username}
                    ))
        self.check_posts_context(response.context['page_obj'][0])
        self.assertEqual(response.context['author'],
                         ViewsTest.post.author)

    def test_profile_detail_context(self):
        """"Из вью post_detail передается правильный контекст."""
        response = self.authorized_client.get(reverse('posts:post_detail',
                                              kwargs={'post_id':
                                                      ViewsTest.post.pk}))
        self.check_posts_context(response.context['post'])

    def test_image_is_there(self):
        """В шаблон передается контекст с картинкой, а не хухры-мухры"""
        names = [reverse('posts:index'),
                 reverse('posts:group',
                         kwargs={'slug': ViewsTest.group.slug}),
                 reverse('posts:profile',
                         kwargs={'username':
                                 ViewsTest.authoruser.username}),
                 ]
        for name in names:
            with self.subTest(reverse=reverse):
                response = self.authorized_client.get(name)
                post = response.context.get('page_obj')[0]
                self.assertEqual(post.image, ViewsTest.post.image)

    def test_new_comment_appears(self):
        text = 'This is me!'
        self.authorized_client.post(reverse('posts:add_comment',
                                    kwargs={'post_id': ViewsTest.post.pk}),
                                    {'text': text}
                                    )
        response = self.authorized_client.get(reverse('posts:post_detail',
                                              kwargs={'post_id':
                                                      ViewsTest.post.pk}
                                                      ))
        comment_from_response = response.context['comments'][0].text
        self.assertEqual(comment_from_response, text)

    def test_cache(self):
        """Берем респонз с главной страницы, запиливаем новый пост,
        обновляем респонз с главной страницы, смотрим, появился ли он там,
        если нет - ок. Дальше чистим кэш и снова далем запрос - пост появился-
        кэш работает.
        """
        response_old = self.guest_client.get(reverse('posts:index'))
        Post.objects.create(text='test2', author=ViewsTest.authoruser)
        response_new = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(response_old.content, response_new.content)
        cache.clear()
        response_cash_clr = self.guest_client.get(reverse('posts:index'))
        self.assertNotEqual(response_new.content, response_cash_clr.content)

    def test_follow(self):
        """Юзер фолловит юзера - появляется новый фоллоу объект,
        автор совпадает с автором, все счастливы
        """
        count_follows = Follow.objects.count()

        self.authorized_client.get(reverse('posts:profile_follow',
                                   kwargs={'username': ViewsTest.notauthoruser}
                                           ))
        count = Follow.objects.all().count()
        self.assertEqual(count, count_follows + 1)
        self.assertEqual(Follow.objects.latest('id').author,
                         ViewsTest.notauthoruser)
        self.assertEqual(Follow.objects.latest('id').user,
                         ViewsTest.authoruser)

    def test_unfollow(self):
        Follow.objects.create(user=ViewsTest.authoruser,
                              author=ViewsTest.notauthoruser)
        count_follow = Follow.objects.count()
        self.authorized_client.get(reverse('posts:profile_unfollow',
                                   kwargs={'username':
                                           ViewsTest.notauthoruser}))
        count_following = Follow.objects.all().count()
        self.assertEqual(count_following, count_follow - 1)

    def test_follow_index(self):
        """ Юзер фолловит автора, автор пишет пост, пост появляется у
        зафолловившего юзера, а у незафолловившего - не появляется.
        """
        pushkin_user = User.objects.create_user(username='pushkin666')
        self.authorized_client.get(reverse('posts:profile_follow',
                                   kwargs={'username': pushkin_user}
                                           ))
        pushkin_post = Post.objects.create(author=pushkin_user,
                                           text='Буря мглою небо кроет')
        response_follower = self.authorized_client.get(
            reverse('posts:follow_index'))
        response_notfollower = self.not_follower_client.get(
            reverse('posts:follow_index'))
        self.assertEqual(len(response_follower.context['page_obj']), 1)
        self.assertEqual(len(response_notfollower.context['page_obj']), 0)
        self.assertEqual(response_follower.context['page_obj'][0].text,
                         pushkin_post.text)
