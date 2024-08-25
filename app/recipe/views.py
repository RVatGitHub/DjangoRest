from rest_framework import viewsets, mixins
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.models import Recipe, Tag, Ingredient
from recipe import serializers


class RecipeViewSet(viewsets.ModelViewSet):

    serializer_class = serializers.RecipeDetailSerializer
    queryset = Recipe.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user).order_by('-id')

    def get_serializer_class(self):
        # return the serializer class for request !important
        if self.action == 'list':
            return serializers.RecipeSerializer

        return self.serializer_class

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class BaseRecipeAttrSet(
    mixins.DestroyModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


    def get_queryset(self):
        return self.queryset.filter(user=self.request.user).order_by('-id')

#understand meaning of these Base class that are being extended
class TagViewSet(BaseRecipeAttrSet):

    serializer_class = serializers.TagSerializer
    queryset = Tag.objects.all()




class IngredientViewSet(BaseRecipeAttrSet):
    # manage ingredients in the database
    serializer_class = serializers.IngredientSerializer
    queryset = Ingredient.objects.all()

