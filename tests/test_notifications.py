"""
tests/test_notifications.py — Mixtape

Tests for notifications created when a song is rated.
"""

import pytest
from app import create_app, db
from models import User, Song, Notification
from services.notification_service import rate_song


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def setup(app):
    with app.app_context():
        sharer = User(username="sharer", email="sharer@example.com")
        rater = User(username="rater", email="rater@example.com")
        db.session.add_all([sharer, rater])
        db.session.flush()

        song = Song(
            title="Test Song", artist="Test Artist",
            genre="indie", shared_by=sharer.id
        )
        db.session.add(song)
        db.session.commit()

        yield {
            "sharer_id": sharer.id,
            "rater_id": rater.id,
            "song_id": song.id,
        }


def test_rating_notifies_song_sharer(app, setup):
    """Rating someone else's song creates a song_rated notification for the sharer."""
    with app.app_context():
        rate_song(setup["rater_id"], setup["song_id"], 5)
        notes = Notification.query.filter_by(user_id=setup["sharer_id"]).all()
        assert len(notes) == 1
        assert notes[0].notification_type == "song_rated"


def test_rating_own_song_does_not_notify(app, setup):
    """Rating your own song creates no notification."""
    with app.app_context():
        rate_song(setup["sharer_id"], setup["song_id"], 5)
        assert Notification.query.filter_by(user_id=setup["sharer_id"]).count() == 0