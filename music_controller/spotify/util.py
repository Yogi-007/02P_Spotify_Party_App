from .models import SpotifyToken
from django.utils import timezone
from datetime import timedelta
from .credentials import CLIENT_ID, CLIENT_SECRET
from requests import post, put, get

BASE_URL = "https://api.spotify.com/v1/me/"


# checks and returns if a session_id/session_key/user has a existing SpotifyToken Object
# if yes returns that object else returns None
def get_user_tokens(session_id):
    user_tokens = SpotifyToken.objects.filter(
        user=session_id)  # list of tokens
    print(user_tokens)
    if user_tokens.exists():
        return user_tokens[0]  # the only token
    else:
        return None


# reciveing all the token data and updates existing SpotifyToken or creates a new SpotifyToken
def update_or_create_user_tokens(session_id, access_token, token_type, expires_in, refresh_token):
    # using above function to determine exists or no
    tokens = get_user_tokens(session_id)
    # changing seconds to valid time stamp and storing in the same variable
    expires_in = timezone.now() + timedelta(seconds=expires_in)

    if tokens:
        # update model of respective session_id as user , update respective datas
        tokens.access_token = access_token
        tokens.refresh_token = refresh_token
        tokens.expires_in = expires_in
        tokens.token_type = token_type
        tokens.save(update_fields=['access_token',
                                   'refresh_token', 'expires_in', 'token_type'])
    else:
        # creating a new data entry and saving the data
        tokens = SpotifyToken(user=session_id, access_token=access_token,
                              refresh_token=refresh_token, token_type=token_type, expires_in=expires_in)
        tokens.save()


# checking for expiry of time to determine and send a new request to spotify with refresh tokens
# checks for existance of data entry / tokens in data base else sends false to front end via view end point
def is_spotify_authenticated(session_id):
    tokens = get_user_tokens(session_id)
    if tokens:
        expiry = tokens.expires_in
        if expiry <= timezone.now():
            refresh_spotify_token(session_id)

        return True

    return False


# to send refresh tokens to spotify recieve all other tokens again
# calling update_or_create_user_tokens to save the new info
def refresh_spotify_token(session_id):
    refresh_token = get_user_tokens(session_id).refresh_token
    response = response = post('https://accounts.spotify.com/api/token', data={
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }).json()

    access_token = response.get('access_token')
    token_type = response.get('token_type')
    expires_in = response.get('expires_in')

    update_or_create_user_tokens(
        session_id, access_token, token_type, expires_in, refresh_token)


# send and recives requests from spotify api has put , post and get used to find current playing song
# and also handles operations like skip/pause songs etc..
def execute_spotify_api_request(session_id, endpoint, post_=False, put_=False):
    # get all tokens of host of the room
    tokens = get_user_tokens(session_id)
    # preping json to send to spotify api along with url end point to hit
    headers = {'Content-Type': 'application/json',
               'Authorization': "Bearer " + tokens.access_token}

    # sending appropriate requests
    if post_:
        post(BASE_URL + endpoint, headers=headers)
    if put_:
        response = put(BASE_URL + endpoint, headers=headers)

    # default get if both put and post are false
    response = get(BASE_URL + endpoint, {}, headers=headers)
    try:
        return response.json()
    except:
        return {'Error': 'Issue with request'}


def play_song(session_id):
    return execute_spotify_api_request(session_id, "player/play", put_=True)


def pause_song(session_id):
    return execute_spotify_api_request(session_id, "player/pause", put_=True)


def skip_song(session_id):
    return execute_spotify_api_request(session_id, "player/next", post_=True)
