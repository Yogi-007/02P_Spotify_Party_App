from django.shortcuts import render
from rest_framework import generics, status
from .models import Room
from .serializers import RoomSerializer, CreateRoomSerializer, UpdateRoomSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse

# Create your views here.


# gives all existing rooms as out to /api/room
class RoomView(generics.ListAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    # room_results = Room.objects.filter(id=30)
    # if len(room_results) > 0:  # if session is host and room exists
    #     room = room_results[0]  # get first room
    #     room.delete()


# takes code from sent request and joins person into room used by join page
class JoinRoom(APIView):
    lookup_url_kwarg = 'code'

    def post(self, request, format=None):
        # checking for prev session if no create new session
        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()
        # getting code variable data from request
        code = request.data.get(self.lookup_url_kwarg)
        if code != None:
            # list of all matched rooms type list
            room_result = Room.objects.filter(code=code)
            if len(room_result) > 0:  # if room exists
                room = room_result[0]  # first object in list, type Room
                # saving that a session has a room_code so that it resumes to the room with that code whenever connected
                self.request.session['room_code'] = code
                return Response({'message': "Room Joined!"}, status=status.HTTP_200_OK)
            return Response({'Room Not Found': 'Invalid Room Code.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'Bad Request': 'Code parameter not found in request'}, status=status.HTTP_400_BAD_REQUEST)


# takes code from sent request and retrives all data of that room used by Room.js (after create and after join pages)
class GetRoom(APIView):
    serializer_class = RoomSerializer
    lookup_url_kwarg = 'code'

    def get(self, request, format=None):
        code = request.GET.get(self.lookup_url_kwarg)
        if code != None:
            room = Room.objects.filter(code=code)
            if len(room) > 0:
                data = RoomSerializer(room[0]).data  # python Room to Json
                # creating a bool for checkin is host
                data['is_host'] = self.request.session.session_key == room[0].host
                return Response(data, status=status.HTTP_200_OK)
            return Response({'Room Not Found': 'Invalid Room Code.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'Bad Request': 'Code parameter not found in request'}, status=status.HTTP_400_BAD_REQUEST)


# gets two data vaiarbles in request and if user exists updates and if doesnt creates new room outputs room
class CreateRoomView(APIView):
    serializer_class = CreateRoomSerializer

    def post(self, request, format=None):
        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()

        # compares request data feilds using createroomserialiser
        # and matches to createroomserialiser fields
        serilaizer = self.serializer_class(data=request.data)

        if serilaizer.is_valid():
            guest_can_pause = serilaizer.data.get('guest_can_pause')
            votes_to_skip = serilaizer.data.get('votes_to_skip')
            host = self.request.session.session_key
            queryset = Room.objects.filter(host=host)  # list of all objects
            if queryset.exists():
                room = queryset[0]  # first object in list, the only room
                room.guest_can_pause = guest_can_pause  # updating
                room.votes_to_skip = votes_to_skip  # updating
                room.save(update_fields=[
                          'guest_can_pause', 'votes_to_skip'])  # saving
                # creating a session variable to store present room code
                self.request.session['room_code'] = room.code
                return Response(RoomSerializer(room).data, status=status.HTTP_200_OK)
            else:
                room = Room(host=host, guest_can_pause=guest_can_pause,
                            votes_to_skip=votes_to_skip)  # creates new room object
                room.save()
                self.request.session['room_code'] = room.code
                return Response(RoomSerializer(room).data, status=status.HTTP_201_CREATED)

        return Response({'Bad Request': 'Invalid data...'}, status=status.HTTP_400_BAD_REQUEST)


# for async function in homepage to check if session already has a room and giving room as out
class UserInRoom(APIView):
    def get(self, request, format=None):
        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()
        data = {
            # getting session variable called room_code created in prev api calls
            'code': self.request.session.get('room_code')
        }
        # returns json converted object or none
        return JsonResponse(data, status=status.HTTP_200_OK)


# called in Room.js for Leaving Room leavingButtonPressed
class LeaveRoom(APIView):
    # good practice use delete function not post
    def post(self, request, format=None):
        if 'room_code' in self.request.session:  # if room_code exists in session
            # remove room_code variable value from session
            code = self.request.session.pop('room_code')
            host_id = self.request.session.session_key  # session_key
            # get all the rooms with this session key as host
            room_results = Room.objects.filter(host=host_id)
            if len(room_results) > 0:  # if session is host and room exists
                room = room_results[0]  # get first room
                room.delete()
        return Response({'Message': 'Left Room'}, status=status.HTTP_200_OK)


# takes request from settings page and updates room parameters
class UpdateRoom(APIView):
    serializer_class = UpdateRoomSerializer

    def patch(self, request, format=None):
        if not self.request.session.exists(self.request.session.session_key):
            self.request.session.create()
        # comapres request data to serilazer_class fields
        serilaizer = self.serializer_class(data=request.data)
        if serilaizer.is_valid():
            guest_can_pause = serilaizer.data.get('guest_can_pause')
            votes_to_skip = serilaizer.data.get('votes_to_skip')
            code = serilaizer.data.get('code')
            # list of room objects with that code
            queryset = Room.objects.filter(code=code)
            if not queryset.exists():
                return Response({'Room Not Found': 'Invalid Room Code.'}, status=status.HTTP_404_NOT_FOUND)
            room = queryset[0]  # first room/ only room
            user_id = self.request.session.session_key  # current session key
            # if not host (checks current key with host variable in room object)
            if room.host != user_id:
                return Response({'Un-Authorized': 'You are not the Host of this Room'}, status=status.HTTP_403_FORBIDDEN)
            room.guest_can_pause = guest_can_pause
            room.votes_to_skip = votes_to_skip
            room.save(update_fields=['guest_can_pause', 'votes_to_skip'])
            # sending full room details by roomserialser
            return Response(RoomSerializer(room).data, status=status.HTTP_200_OK)
        return Response({'Bad Request': 'Invalid data...'}, status=status.HTTP_406_NOT_ACCEPTABLE)
