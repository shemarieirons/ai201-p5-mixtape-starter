# Mixtape Bug Hunt Submission

## AI Usage


## Codebase Map

I read each file below and followed three requests down to the commit.

**Main files.**
- `app.py`: holds the shared `db` object and `create_app`, which configures SQLite (or `DATABASE_URL`), calls `db.init_app`, registers four blueprints, and runs `db.create_all`.
- `models.py`: defines the tables, `generate_uuid`, and `to_dict` serializers.
- `routes/songs.py`: `search`, `get_song_detail`, `rate`, `listen`.
- `routes/playlists.py`: `create`, `get_detail`, `get_songs`, `add_song`.
- `routes/users.py`: `get_user`, `streak`, `notifications`, `read_notification`.
- `routes/feed.py`: `listening_now`, `activity`.
- `services/search_service.py`: `search_songs`, `get_song`.
- `services/notification_service.py`: `create_notification`, `add_to_playlist`, `rate_song`, `get_notifications`, `mark_as_read`.
- `services/playlist_service.py`: `create_playlist`, `get_playlist_songs`, `get_playlist`, `get_user_playlists`.
- `services/streak_service.py`: `record_listening_event`, `update_listening_streak`, `get_streak`.
- `services/feed_service.py`: `get_friends_listening_now`, `get_activity_feed`.

**Models.** Every id is a string UUID. `User` stores `username`, `email`, `listening_streak`, and `last_listened_at`, and relates to shared songs, ratings, listening events, notifications, playlists, and friends. `Song` points at its sharer through `shared_by`. `Tag` joins songs through `song_tags`. `Rating` links `user_id` and `song_id`, stores `score`, and has a unique constraint on that pair. `ListeningEvent` links a user and a song with `listened_at`. `Playlist` points at its creator through `created_by` and reaches songs through `playlist_entries`, which carries `position`, `added_by` (a user foreign key), and `added_at`. `Notification` belongs to a recipient through `user_id`. `friendships` is a self-referential many-to-many on `User`.

**Rating a song.** `POST /songs/<song_id>/rate` hits `rate` in `routes/songs.py`. It reads `user_id` and `score` from JSON and returns 400 when either is missing. It then calls `rate_song` in `notification_service.py`. That function rejects a score outside 1 to 5, loads the `Song` and `User` with `db.session.get`, and looks up a `Rating` for that user and song. An existing row gets a new `score`. Otherwise it builds a `Rating`, adds it, and commits. The route returns `rating.to_dict()` with status 201.

**Adding a song to a playlist.** `POST /playlists/<playlist_id>/songs` hits `add_song` in `routes/playlists.py`. It requires `song_id` and `added_by`, then calls `add_to_playlist` in `notification_service.py`. That function loads the `Song`, the adding `User`, and the `Playlist`. When the song is absent from `playlist.songs`, it appends the song and commits, and SQLAlchemy writes the row in `playlist_entries`. When `song.shared_by` differs from the adder, it calls `create_notification`, which inserts a `Notification` for the sharer with type `song_added_to_playlist` and commits. The route returns `{"message": "Song added to playlist"}` with status 201.

**Recording a listen.** `POST /songs/<song_id>/listen` hits `listen` in `routes/songs.py`. It requires `user_id`, then calls `record_listening_event` in `streak_service.py`. That function loads the `User`, adds a `ListeningEvent` for the song at the current UTC time, calls `update_listening_streak` with that user and time, and commits. The route returns `event.to_dict()` with status 201.

**Patterns.** Routes check the request body and wrap results in `jsonify`. Services load models, raise `ValueError` for a missing record or an out-of-range value, and commit. Read routes, plus `read_notification`, turn that into 404. `rate`, `listen`, `create`, and `add_song` turn it into 400. Most routes delegate to a service function. `get_user` is a small exception that looks up the `User` itself. Blueprints mount at `/songs`, `/playlists`, `/users`, and `/feed`. Model classes expose `to_dict` for the JSON those routes send back.

## Root Cause Analyses

**Issue #1 — My listening streak keeps resetting**
- How you reproduced it:
- How you found the root cause:
- The root cause:
- Your fix:
- Your side-effect check:

**Issue #2 — Friends Listening Now shows people from yesterday**
(same five fields)

**Issue #3 — The same song keeps showing up twice in search**
(same five fields)

**Issue #4 — Notification missing when a friend rates a song**
(same five fields)

**Issue #5 — The last song in a playlist never shows up**
(same five fields)

## Regression Test
(test file name, what it verifies, why it fails on the buggy code)