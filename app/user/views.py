# Views for users API.

from rest_framework import generics
from user.serializers import UserSerializer

class CreateUserView(generics.CreateAPIView):
    #Create a new User in the system
    serializer_class = UserSerializer