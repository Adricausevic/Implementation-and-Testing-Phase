import os
import random
from flask import Flask, redirect, request, url_for, session, render_template
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build

# Allow insecure transport for local development
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Flask setup
app = Flask(__name__, static_folder="static")
app.secret_key = os.urandom(24)

# Google API credentials
CLIENT_CONFIG = {
    "web": {
        "client_id": "653989477873-q8a7r6m93eh4q2m4e15pndikknggp9n4.apps.googleusercontent.com",
        "project_id": "youtube-api-project-443317",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "YOUR_CLIENT_SECERET",
        "redirect_uris": ["http://127.0.0.1:5000/callback"],
    }
}

# Updated SCOPES
SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly"
]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

@app.route("/")
def home():
    return render_template("Login.html")

@app.route("/emotion_selection")
def emotion_selection():
    if "credentials" not in session:
        return redirect(url_for("authorize"))
    emotions = ["Happy", "Sad", "Energetic", "Calm"]
    return render_template("emotion_selection.html", emotions=emotions)

@app.route("/generate_playlist", methods=["POST"])
def generate_playlist():
    selected_emotion = request.form.get("emotion")
    if not selected_emotion:
        return "Error: No emotion selected", 400
    session["selected_emotion"] = selected_emotion
    return redirect(url_for("playlist"))

@app.route("/playlist")
def playlist():
    if "credentials" not in session:
        return redirect(url_for("authorize"))

    credentials = google.oauth2.credentials.Credentials(**session["credentials"])
    youtube = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

    selected_emotion = session.get("selected_emotion", "Unknown")
    videos = get_videos_for_emotion(youtube, selected_emotion)
    if not videos:
        return "No videos found. Please try again later."

    playlist_id = create_named_playlist(youtube, selected_emotion, videos)
    youtube_playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"

    return redirect(youtube_playlist_url)

def get_videos_for_emotion(youtube, emotion):
    emotion_to_keywords = {
        "Happy": "feel-good songs official music video",
        "Sad": "emotional songs official music video",
        "Energetic": "upbeat songs official music video",
        "Calm": "relaxing acoustic songs official music video",
    }
    keywords = emotion_to_keywords.get(emotion, "official music video")

    # Step 1: Fetch user's liked videos
    liked_videos_request = youtube.videos().list(
        part="snippet",
        myRating="like",
        maxResults=20
    )
    liked_videos_response = liked_videos_request.execute()

    liked_videos = [
        {
            "title": item["snippet"]["title"],
            "videoId": item["id"],
            "channel": item["snippet"]["channelTitle"]
        }
        for item in liked_videos_response.get("items", [])
        if "official" in item["snippet"]["title"].lower()
    ]

    # Step 2: Fetch emotion-based recommendations
    search_request = youtube.search().list(
        part="snippet",
        q=keywords,
        type="video",
        videoCategoryId="10",
        maxResults=20
    )
    search_response = search_request.execute()

    emotion_based_videos = [
        {
            "title": item["snippet"]["title"],
            "videoId": item["id"]["videoId"],
            "channel": item["snippet"]["channelTitle"]
        }
        for item in search_response.get("items", [])
        if "official" in item["snippet"]["title"].lower()
    ]

    # Combine watched and emotion-based videos
    combined_videos = liked_videos + emotion_based_videos

    # Remove duplicates by videoId
    unique_videos = {video["videoId"]: video for video in combined_videos}.values()

    # Randomize results for variety
    shuffled_videos = list(unique_videos)
    random.shuffle(shuffled_videos)

    # Return top 20 unique videos
    return shuffled_videos[:20]

def create_named_playlist(youtube, emotion, videos):
    playlist_title = f"{emotion.capitalize()} Mood Playlist"
    playlist_description = f"A curated playlist for a {emotion.lower()} mood."
    playlist_request = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": playlist_title,
                "description": playlist_description,
                "tags": ["mood", emotion, "music", "YouTube"],
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": "public"
            }
        }
    )
    playlist_response = playlist_request.execute()
    playlist_id = playlist_response["id"]

    for video in videos:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video["videoId"]
                    }
                }
            }
        ).execute()

    return playlist_id

@app.route("/authorize")
def authorize():
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        CLIENT_CONFIG, scopes=SCOPES
    )
    flow.redirect_uri = url_for("callback", _external=True)
    authorization_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true"
    )
    session["state"] = state
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    state = session["state"]
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        CLIENT_CONFIG, scopes=SCOPES, state=state
    )
    flow.redirect_uri = url_for("callback", _external=True)
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    session["credentials"] = credentials_to_dict(credentials)
    return redirect(url_for("emotion_selection"))

def credentials_to_dict(credentials):
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route('/test-css-url')
def test_css_url():
    return url_for('static', filename='css/loginPageStyle.css')

if __name__ == "__main__":
    app.run(port=5000, debug=True)
