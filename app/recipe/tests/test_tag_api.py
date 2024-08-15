from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase


from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag

from recipe.serializers import TagSerializer

TAGS_URL = reverse('recipe:tag-list')

def create_user(email='test@test.com',password='test123'):
    return get_user_model().objects.create_user(email,password)

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
        allTags = Tag.objects.all().order_by('-name')
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