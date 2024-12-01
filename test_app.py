import unittest
from MoodMelodyYoutube import get_videos_for_emotion, create_named_playlist
from unittest.mock import MagicMock


class TestApp(unittest.TestCase):
    def test_get_videos_for_emotion(self):
        # Mock YouTube API responses
        mock_youtube = MagicMock()
        mock_youtube.videos().list().execute.return_value = {
            "items": [
                {"snippet": {"title": "Happy Song Official", "channelTitle": "Test Channel"},
                 "id": "12345"}
            ]
        }
        mock_youtube.search().list().execute.return_value = {
            "items": [
                {"snippet": {"title": "Another Happy Song Official", "channelTitle": "Test Channel"},
                 "id": {"videoId": "67890"}}
            ]
        }

        videos = get_videos_for_emotion(mock_youtube, "Happy")
        self.assertGreater(len(videos), 0)  # Ensure videos are returned
        self.assertIn("Happy Song Official", [video["title"] for video in videos])

    def test_create_named_playlist(self):
        # Mock YouTube API responses for playlist creation
        mock_youtube = MagicMock()
        mock_youtube.playlists().insert().execute.return_value = {"id": "test_playlist_id"}
        mock_youtube.playlistItems().insert().execute.return_value = {}

        # Sample videos for the playlist
        videos = [
            {"title": "Happy Song Official", "videoId": "12345", "channel": "Test Channel"},
            {"title": "Another Happy Song Official", "videoId": "67890", "channel": "Test Channel"}
        ]

        playlist_id = create_named_playlist(mock_youtube, "Happy", videos)
        self.assertEqual(playlist_id, "test_playlist_id")  # Ensure correct playlist ID is returned


if __name__ == "__main__":
    unittest.main()

