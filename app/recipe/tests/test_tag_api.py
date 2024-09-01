from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag, Recipe

from recipe.serializers import TagSerializer

TAGS_URL = reverse('recipe:tag-list')

def create_user(email='test@test.com',password='test123'):
    return get_user_model().objects.create_user(email,password)

def get_detail_url(id):
    return reverse('recipe:tag-detail', args=[id])

class PublicTagsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(TAGS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateTagsApiTests(TestCase):

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        Tag.objects.create(user=self.user, name='vegan')
        Tag.objects.create(user=self.user, name='non-vegan')

        #Network fetch
        res = self.client.get(TAGS_URL)

        #database fetch
        allTags = Tag.objects.all().order_by('-id')
        # serialize after database fetch
        serializer = TagSerializer(allTags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data,serializer.data)

    def test_tags_limited_to_user(self):

        user2 = create_user(email='second@sec.ss')
        Tag.objects.create(user=user2, name='egg')

        tag = Tag.objects.create(user=self.user,name='vegan')

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)

    def test_update_tag(self):
        tag = Tag.objects.create(user=self.user, name='vegan')
        payload = {
            'name': 'non-vegan'
        }
        url = get_detail_url(tag.id)
        res = self.client.patch(url,payload)
        tag.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        tag = Tag.objects.create(user=self.user, name='vegan')

        url = get_detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        tags = Tag.objects.filter(user=self.user)
        self.assertFalse(tags.exists())


    def test_filter_tags_assigned_to_Recipes(self):
        tag1 = Tag.objects.create(user=self.user, name='kid')
        tag2 = Tag.objects.create(user=self.user, name='adult')

        recipe = Recipe.objects.create(
            title='name',
            time_minutes=44,
            price = Decimal('44.4'),
            user=self.user
        )
        recipe.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)