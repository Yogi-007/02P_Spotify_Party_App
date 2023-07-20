from rest_framework import serializers
from .models import Room


# converts data from python dict to json format here used to get info from db
class RoomSerializer(serializers.ModelSerializer):
    class Meta():
        model = Room
        fields = ('id', 'code', 'host', 'guest_can_pause',
                  'votes_to_skip', 'created_at')


# converts data from python dict to json format used to post to db
class CreateRoomSerializer(serializers.ModelSerializer):
    class Meta():
        model = Room
        fields = ('guest_can_pause', 'votes_to_skip')


class UpdateRoomSerializer(serializers.ModelSerializer):
    code = serializers.CharField(validators=[])

    class Meta:
        model = Room
        fields = ('guest_can_pause', 'votes_to_skip', 'code')
