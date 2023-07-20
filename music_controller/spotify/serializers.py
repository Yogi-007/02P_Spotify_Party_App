from rest_framework import serializers
from .models import SpotifyToken


class SpotifyTokenSerializer(serializers.ModelSerializer):
    class Meta():
        model = SpotifyToken
        fields = ('id', 'user', 'created_at', 'refresh_token',
                  'access_token', 'expires_in', 'token_type')
