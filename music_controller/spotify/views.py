from django.shortcuts import render, redirect
from .credentials import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
from rest_framework.views import APIView
from requests import Request, post
from rest_framework import status, generics
from rest_framework.response import Response
from .util import *
from api.models import Room
from .serializers import SpotifyTokenSerializer
from .models import Vote, SpotifyToken


# this is called in front end to get a url back with our app data
# our app data: client_id, client_secret, redirect_uri
class SpotifyTokenView(generics.ListAPIView):
    queryset = SpotifyToken.objects.all()
    serializer_class = SpotifyTokenSerializer
    token_db_entry = SpotifyToken.objects.filter(id=14)
    if len(token_db_entry) > 0:
        db_entry = token_db_entry[0]
        db_entry.delete()


class AuthURL(APIView):
    def get(self, request, format=None):
        # tells spotify what all accesses we need, sent via front-end, user allows all this for our app to control
        scopes = 'user-read-playback-state user-modify-playback-state user-read-currently-playing'

        # url that is sent to user when he hits this AuthURL View endpoint
        # it specifies where to go (Spotify link) and what data(our client_id) to send in the request
        # also says in data that we need a code back from spotify caught by frontend and returned later
        # doesnt send a request to spotify just sends to front-end what request to send where
        url = Request('GET', 'https://accounts.spotify.com/authorize', params={
            'scope': scopes,
            'response_type': 'code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID
        }).prepare().url

        return Response({'url': url}, status=status.HTTP_200_OK)


# after user authrised by spotify we get a code from spotify as response in front-end
# front end now calls this callback function passing that code(and error) in request parameter
def spotify_callback(request, format=None):
    # getting the response code from spotify after authurl request from front-end
    code = request.GET.get('code')
    error = request.GET.get('error')

    # new response sent to spotify with code, our data
    # ourdata : client_id, client_secret and redirect_uri
    # this also sends request directly to spotify gets the response convert to json
    response = post('https://accounts.spotify.com/api/token', data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }).json()

    # spotify after recieving that request(with code) sends back a response with all the tokens (access, refresh, expires..)
    # retiving all that that data/tokens from the recieved response(converted to json)
    access_token = response.get('access_token')
    token_type = response.get('token_type')
    refresh_token = response.get('refresh_token')
    expires_in = response.get('expires_in')
    error = response.get('error')

    # if no session create session
    if not request.session.exists(request.session.session_key):
        request.session.create()

    # saving all the tokens into a new model
    # using below function from util.py to check for already existing user then update the model else create new user data/model entry
    update_or_create_user_tokens(
        request.session.session_key, access_token, token_type, expires_in, refresh_token)

    return redirect('frontend:')


# end point for checking for expiry
class IsAuthenticated(APIView):
    def get(self, request, format=None):
        is_authenticated = is_spotify_authenticated(
            self.request.session.session_key)

        return Response({'status': is_authenticated}, status=status.HTTP_200_OK)

# get currently playing song


class CurrentSong(APIView):
    def get(self, request, format=None):
        # getting session room code (guest or host)
        room_code = self.request.session.get('room_code')
        # getting that room code's room object
        room = Room.objects.filter(code=room_code)
        if room.exists():
            room = room[0]
        else:
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        # getting the host of that room
        host = room.host
        # def end point used by the next function in util.py
        endpoint = "player/currently-playing"
        # get request to get current song details
        response = execute_spotify_api_request(host, endpoint)

        # if returned response from the above function returned by spotify has errors sorry :(
        if 'error' in response:
            return Response({}, status=status.HTTP_204_NO_CONTENT)
        if 'item' not in response:
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        # seperating all the data we need from whats returned by spotify
        item = response.get('item')
        duration = item.get('duration_ms')
        progress = response.get('progress_ms')
        album_cover = item.get('album').get('images')[0].get('url')
        is_playing = response.get('is_playing')
        song_id = item.get('id')

        artist_string = ""
        # multiple artists
        for i, artist in enumerate(item.get('artists')):
            if i > 0:
                artist_string += ", "
            name = artist.get('name')
            artist_string += name

        # passing all the filtered data and making a dict to pass to front end
        votes = len(Vote.objects.filter(room=room, song_id=song_id))
        song = {
            'title': item.get('name'),
            'artist': artist_string,
            'duration': duration,
            'time': progress,
            'image_url': album_cover,
            'is_playing': is_playing,
            'votes': votes,
            'votes_required': room.votes_to_skip,
            'id': song_id
        }
        self.update_room_song(room, song_id)
        return Response(song, status=status.HTTP_200_OK)

    def update_room_song(self, room, song_id):
        current_song = room.current_song

        if current_song != song_id:
            room.current_song = song_id
            room.save(update_fields=['current_song'])
            votes = Vote.objects.filter(room=room).delete()


# calls util.py function to put request to spotify
class PauseSong(APIView):
    def put(self, response, format=None):
        room_code = self.request.session.get('room_code')
        room = Room.objects.filter(code=room_code)[0]
        if self.request.session.session_key == room.host or room.guest_can_pause:
            pause_song(room.host)
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        return Response({}, status=status.HTTP_403_FORBIDDEN)


# calls util.py function to put request to spotify
class PlaySong(APIView):
    def put(self, response, format=None):
        room_code = self.request.session.get('room_code')
        room = Room.objects.filter(code=room_code)[0]
        if self.request.session.session_key == room.host or room.guest_can_pause:
            play_song(room.host)
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        return Response({}, status=status.HTTP_403_FORBIDDEN)


class SkipSong(APIView):
    def post(self, request, format=None):
        room_code = self.request.session.get('room_code')
        room = Room.objects.filter(code=room_code)[0]
        votes = Vote.objects.filter(room=room, song_id=room.current_song)
        votes_needed = room.votes_to_skip

        if self.request.session.session_key == room.host or len(votes) + 1 >= votes_needed:
            votes.delete()
            skip_song(room.host)
        else:
            vote = Vote(user=self.request.session.session_key,
                        room=room, song_id=room.current_song)
            vote.save()

        return Response({}, status.HTTP_204_NO_CONTENT)
