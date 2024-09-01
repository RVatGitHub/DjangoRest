

from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
    TagSerializer
)

RECIPE_URL = reverse('recipe:recipe-list')

def get_recipe_detail(id):
    return reverse('recipe:recipe-detail',args=[id])

def image_upload_url(id):
    return reverse('recipe:recipe-upload-image', args=[id])

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
        res = self.client.post(RECIPE_URL, payload, format='json')

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


    def test_create_recipe_with_new_tags(self):
        payload={
            'title': 'somedish',
            'time_minutes': 90,
            'price': Decimal('4.44'),
            'tags': [{'name': 'thai'}, {'name': 'indian'}]
        }
        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)


    def test_create_recipe_with_existing_tags(self):

        tag_indian = Tag.objects.create(user=self.user, name='Indian')
        payload = {
            'title': 'pongal',
            'time_minutes': 45,
            'price': Decimal('4.55'),
            'tags': [{'name': 'Indian'}, {'name': 'Breakfast'}]
        }
        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            self.assertTrue(recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists())

    def test_create_tag_on_update(self):

        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name': 'Lunch'}]}
        url = get_recipe_detail(recipe.id)
        res = self.client.patch(url, payload, format= 'json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(),1)
        self.assertTrue(recipe.tags.filter(name=payload['tags'][0]['name'], user=self.user).exists())
        new_tag = Tag.objects.create(user=self.user, name='Lunch')
        self.assertTrue(Tag.objects.count(), 1)

    def test_update_recipe_assign_tag(self):

        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {'tags': [{'name': 'Lunch'}]}

        url = get_recipe_detail(recipe.id)
        res = self.client.patch(url, payload, format = 'json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tag(self):

        tag = Tag.objects.create(user=self.user, name='Dessert')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {'tags':[]}
        url = get_recipe_detail(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)


    def test_create_recipe_with_new_ingredient(self):

        payload = {
            'title': 'some',
            'time_minutes': 44,
            'price': Decimal('4.30'),
            'ingredients': [{'name':'Cauliflower'},{'name': 'Salt'}],
        }

        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(),1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            self.assertTrue(recipe.ingredients.filter(
                user=self.user,
                name=ingredient['name']
            ).exists())


    def test_create_recipe_with_existing_ingredient(self):

        ingredient = Ingredient.objects.create(user=self.user, name='Lemon')
        paylaod = {
            'title': 'some',
            'time_minutes': 99,
            'price': Decimal('3.33'),
            'ingredients': [{
                'name': 'Lemon'
            },
            {
                'name': 'fish sauce'
            }
            ]
        }
        res = self.client.post(RECIPE_URL, paylaod, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(),1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient, recipe.ingredients.all())
        for ingredient in paylaod['ingredients']:
            self.assertTrue(recipe.ingredients.filter(
                user=self.user,
                name=ingredient['name']
            ).exists())

    def test_create_ingredient_on_update(self):

        recipe = create_recipe(user=self.user)

        payload = {'ingredients': [{'name': 'lemon'}]}
        url = get_recipe_detail(recipe.id)
        res= self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(user=self.user, name='lemon')
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):

        ingredient = Ingredient.objects.create(user=self.user, name='Pepper')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        ingredient2 = Ingredient.objects.create(user=self.user, name='chilli')
        payload = {'ingredients': [{'name': 'chilli'}]}
        url = get_recipe_detail(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):

        ingredient = Ingredient.objects.create(user=self.user, name='garlic')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {'ingredients': []}
        url = get_recipe_detail(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(),0)


class ImageUploadTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'password123'
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)


    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):

        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format= 'multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):

        url = image_upload_url(self.recipe.id)
        payload = {'image': 'notanimage'}
        res = self.client.post(url, payload, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
