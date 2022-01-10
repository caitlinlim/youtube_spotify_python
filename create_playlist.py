import json
import requests

# YouTube data API
import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors


import youtube_dl

from exceptions import ResponseException
from secrets import user_id, token


class CreatePlaylist:

    def __init__(self):
        self.user_id = user_id
        self.spotify_token = token

        # Call Function 1
        self.youtube_client = self.get_youtube_client()
        # Empty dictionary of song information including track and artist name
        self.all_songs_info = {}

    # 1. Log into YouTube
    def get_youtube_client(self):
        # Copied from YouTube data API
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "client_secret.json"

        # Get credentials and create an API client
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes)
        credentials = flow.run_console()
        youtube = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials)

        return youtube

    # 2. Grab liked videos
    def get_liked_videos(self):
        # Referred to YouTube data API
        # list (my liked videos)
        # This example retrieves a list of videos liked by the user authorizing the API request.
        request = self.youtube_client.videos().list(
            part="snippet,contentDetails,statistics",
            myRating="like"
        )
        response = request.execute()

        # json output
        # video title: navigate through items -> snippet -> title
        # video url: items -> id
        for item in response["items"]:
            video_title = item["snippet"]["title"]
            video_url = "https://www.youtube.com/watch?v={}".format(item["id"])

            # Use YouTube_dl to parse out track and artist
            # We just want to extract, not download
            ydl = youtube_dl.YoutubeDL({}).extract_info(video_url, download=False)
            track = ydl["track"]
            artist = ydl["artist"]

            if track is not None and artist is not None:
                self.all_songs_info[video_title] = {
                    "youtube_url": video_url,
                    "artist": artist,
                    "track": track,

                    # Get spotify uri using function 4
                    "spotify_uri": self.get_spotify_uri(track, artist)
                }

    # 3. Create a new Spotify playlist
    def create_playlist(self):

        # Request body from Spotify Web API
        x = {
            "name": "YouTube Liked Videos",
            "description": "All Liked YouTube Videos",
            "public": True
        }

        # Convert Python object into a json string.
        request_body = json.dumps(x)

        # Endpoint using user ID from secrets.py
        query = "https://api.spotify.com/v1/users/{}/playlists".format(self.user_id)

        # Make a POST request to query, and return the response text
        # Curl -X "POST" on Spotify Web API
        response = requests.post(
            query,
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        )

        # Returns a JSON object of the result
        response_json = response.json()

        # Return playlist id
        return response_json["id"]

    # 4. Search for a song
    def get_spotify_uri(self, song_name, artist):

        # Endpoint using the song name and the artist
        query = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=20".format(
            song_name,
            artist
        )

        # Make a POST request to query, and return the response text
        # GET https://api.spotify.com/v1/search
        response = requests.get(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        )

        # Returns a JSON object of the result
        response_json = response.json()

        # Return songs and grab uri of the first song
        songs = response_json["tracks"]["items"]
        uri = songs[0]["uri"]

        # Return uri of song
        return uri

    # 5. Add this song into new Spotify playlist
    def add_song_to_playlist(self):

        # Call Function 2: Populate songs dictionary
        self.get_liked_videos()

        # Get the uris
        uris = [info["spotify_uri"]
                for song, info in self.all_songs_info.items()]

        # Call Function 3: Create playlist
        playlist_id = self.create_playlist()

        # Convert Python object into a json string
        request_data = json.dumps(uris)

        # Endpoint using playlist ID from Function 3
        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(playlist_id)

        # Make a POST request to query, and return the response text
        # Curl -X "POST" on Spotify Web API
        response = requests.post(
            query,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        )

        # Returns a JSON object of the result
        response_json = response.json()

        return response_json


# Call program
if __name__ == '__main__':
    cp = CreatePlaylist()
    cp.add_song_to_playlist()
