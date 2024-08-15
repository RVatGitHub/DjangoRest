

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer
)

RECIPE_URL = reverse('recipe:recipe-list')

def get_recipe_detail(id):
    return reverse('recipe:recipe-detail',args=[id])

def create_recipe(user, **params):

    default = {
        'title': 'Sample recipe title',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'description': 'Sample Description',
        'link': 'http://example.com/recipe.pdf'
    }
    default.update(params)

    recipe = Recipe.objects.create(user=user, **default)
    return recipe



class PublicRecipeAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(RECIPE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

def create_user(email, password):
    return get_user_model().objects.create_user(email,password)

class PrivateRecipeAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            'user@example.com',
            'testpass123'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipe(self):
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res=self.client.get(RECIPE_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        other_user = create_user(
            'other@example.com',
            'password123'
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many = True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)


    def test_get_recipe_detail(self):
        recipe = create_recipe(user=self.user)

        url = get_recipe_detail(recipe.id)

        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        # print("RES TESTING===>", res)
        # print("RESDATA TESTING===>", res.data)
        # print("serializer TESTING===>", serializer)
        # print("serializer data TESTING===>", serializer.data)
        # print("modelRecipe data TESTING===>", recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        payload = {
            'title': 'biryani',
            'description': 'cook',
            'time_minutes': 89,
            'price': Decimal('44.44'),
        }
        res = self.client.post(RECIPE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])

        for k,v in payload.items():
            # self.assertEqual(getattr(res.data,k),v)
            self.assertEqual(getattr(recipe,k),v)

        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        time_minutes = 90
        recipe=create_recipe(self.user, time_minutes=90)
        payload = {
            'title': 'udpated-title'
        }
        url = get_recipe_detail(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.time_minutes, time_minutes)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        recipe = create_recipe(
            user=self.user,
            title='new_rec',
            description='new desc',
            time_minutes=10,
            price=Decimal('22.30'),
            link='https://example.com'
        )
        payload = {
            'title': 'updated-title',
            'description': 'updated-desc',
            'time_minutes': 90,
            'price': Decimal('33.44'),
            'link': 'https://newlink.com'
        }
        url = get_recipe_detail(recipe.id)
        res = self.client.put(url, payload)
        recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        for k,v in payload.items():
            self.assertEqual(getattr(recipe,k),v)
        self.assertEqual(recipe.user,self.user)

    def test_update_user_returns_error(self):
        new_user = create_user('newuser@edx.ddd','passwer')
        recipe = create_recipe(self.user)
        url = get_recipe_detail(recipe.id)
        res = self.client.patch(url, {'user': new_user.id })
        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        recipe = create_recipe(user=self.user)
        url = get_recipe_detail(recipe.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_other_users_recipe_error(self):
        new_user = create_user('newuser@examo.com','newuser123')
        new_recipe = create_recipe(new_user)
        url = get_recipe_detail(new_recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=new_recipe.id).exists())

