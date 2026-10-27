# Mixtape Bug Hunt Submission

## AI Usage
I used Cursor for codebase orientation and Claude for reproduction setup, code explanation, verification of my analysis, and the regression test code. I reproduced every bug myself, located the suspicious function in each case myself, wrote each root cause analysis myself, and ran every verification command. The AI helped me understand code I had already found and checked work I had already written.

Codebase orientation (Cursor). After reading README.md, I asked Cursor to summarize each file’s responsibility and trace what happens when a user rates a song and when a song is added to a playlist. I checked its draft against the code: rate_song and add_to_playlist both live in services/notification_service.py, search_service.py defines only search_songs and get_song, and the 400 and 404 status codes match the real return statements. One claim was wrong: it implied adding a song fills every column on playlist_entries. I checked add_to_playlist, models.py and seed_data.py and rewrote it to describe only what the function does. I added the “recording a listen” flow from my own reading of record_listening_event.

Reproduction (my own hands-on work). Claude suggested the approach, and I ran every command and recorded the results. For #3 I compared tag counts with search result counts (0 tags: 1 result, 1 tag: 1, 3 tags: 3). For #5 I compared len(playlist.songs), which was 7, with the API’s 6 results, then queried playlist_entries and saw positions 1 to 7. For #4 I rated a song and checked the owner’s notifications. For #1 I called update_listening_streak with controlled Saturday-to-Sunday and Monday-to-Tuesday dates. For #2 I called the listening-now endpoint and saw listens from the previous UTC day.

Investigation and root cause analysis. For each bug, I traced the code myself from the route to the service function and located the suspicious code before involving AI. I then used Claude to help me understand what that code does. I wrote each root cause analysis myself and afterward asked Claude to verify it against the code. I checked each claim against my own data: the Sunday-only reset matched weekday() returning 6 for Sunday, the 7 rows versus 6 results matched the slice, and the duplicate count matched the tag count.

Regression test. Claude gave me the regression test code for Issue #4. I ran it, checked its fixtures against tests/test_search.py, and proved it fails without the fix (assert 0 == 1). I did the same for the shipped Sunday streak test (assert 1 == 2).

Where the AI was wrong or incomplete.

Claude guessed the Notification field was named type, and later suggested a type versus notification_type mismatch. Both were wrong. My shell raised AttributeError, so I printed n.to_dict() and found the attribute is notification_type, exposed as “type”.
My edit to rate_song pasted in the whole body of add_to_playlist, using variables that do not exist there. Claude flagged it and I removed the extra lines.
Claude told me to run tests/test_streak.py but the file is test_streaks.py. pytest said “file not found”, so I listed the folder.
Claude’s test count was off once. I ran pytest and used the real result, 15 passed.
My old server was still running after my edit (debug mode off, port 5000 in use), so my first Issue #4 test would have been invalid. I restarted it first.

What I did myself. I ran every reproduction and verification, made each edit, committed one fix per commit, and ran the side-effect checks (both sides of the boundary for #1, #2 and #5, the own-song and re-rate cases for #4, artist search and tag output for #3).

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

**Issue #1: My listening streak keeps resetting**

- **How you reproduced it:** Today is not a Sunday, so I called `update_listening_streak` directly in `flask shell` with controlled dates and an unsaved `User` (never added to the session, so nothing was written). I set `listening_streak = 12` and `last_listened_at` to Saturday 2026-10-24 20:00 UTC, then called `update_listening_streak(user, Sunday 2026-10-25 09:00 UTC)`. The streak came back as 1 instead of 13. As a control I used Monday 2026-10-26 20:00 to Tuesday 2026-10-27 09:00 with the same starting streak of 12, and it correctly returned 13. Same one-day gap, different result, so the weekday mattered.

- **How you found the root cause:** The report said both resets happened on a Sunday, which pointed at a weekday-specific condition rather than general date math. I started at `GET /users/<id>/streak` in `routes/users.py`, which calls `get_streak`. That function only returns the stored `listening_streak`, so the logic had to be in whatever writes it. Following `POST /songs/<id>/listen` led from `routes/songs.py` to `record_listening_event` in `services/streak_service.py`, which calls `update_listening_streak`. I read that function against its own docstring, which lists four rules and mentions no weekdays, and found `elif days_since_last == 1 and today.weekday() != 6`. Python's `weekday()` returns 0 for Monday through 6 for Sunday, so that extra clause was the specific cause, not just a suspicious area. My reproduction matched: the failing run had a Sunday as "today" and the control did not.

- **The root cause:** In `update_listening_streak`, the branch that increments the streak was `elif days_since_last == 1 and today.weekday() != 6`. On a Sunday, `today.weekday()` is 6, so the second half of the condition was False even when `days_since_last` was exactly 1 (the user had listened the day before). Python skipped the increment branch and fell into the final `else`, which sets `listening_streak = 1`. A perfectly consecutive Saturday-to-Sunday listen was therefore treated like a skipped day. It only happened on Sundays because 6 is the only weekday value that makes the extra clause False. Correct behavior has to depend only on the number of calendar days between listens, as the docstring says: a listen the day after the previous one extends the streak regardless of which weekday it falls on.

- **Your fix:** I removed `and today.weekday() != 6`, leaving `elif days_since_last == 1:` in `services/streak_service.py`. This fixes the cause rather than the symptom: the increment decision now depends only on the day difference, which is what the docstring rules describe.

- **Your side-effect check:** The other branches (first-ever listen, same day, gap of more than one day) were not edited, but I re-ran them to be sure. In `flask shell` with a starting streak of 12: Saturday to Sunday gave 13 (it was 1 before), Monday to Tuesday gave 13, a two-day gap (Friday to Sunday) gave 1, and two listens on the same day left the streak at 12. Together these show the Sunday case changed while the reset and same-day logic did not. I also ran the existing tests: `test_streak_increments_on_sunday` in `tests/test_streaks.py` fails on the old condition (`assert 1 == 2`) and passes with the fix, and the other streak tests pass either way.

**Issue #2: Friends Listening Now shows people from yesterday**

- **How you reproduced it:** I called `GET /feed/<nova_id>/listening-now` with the app running on the seed data. At the time it was about 01:30 UTC on Oct 27 (about 9pm on Oct 26 local time). The response had `count: 3`, listing darius, simone, and kenji, with `listened_at` values between `2026-10-26T23:09` and `2026-10-26T23:19` UTC. Those listens were on the previous UTC calendar day, yet they were shown as "listening now". The three users are nova's friends (confirmed through `user.friends` in `flask shell`).

- **How you found the root cause:** The report said yesterday-evening listens lingered "until the same time the next day", which is the signature of a rolling 24 hour window rather than a calendar-day boundary. I followed `listening_now` in `routes/feed.py` to `get_friends_listening_now` in `services/feed_service.py`. Reading the function top to bottom, the filter on `ListeningEvent.listened_at >= cutoff` uses `cutoff = datetime.now(timezone.utc) - RECENT_THRESHOLD`, and `RECENT_THRESHOLD = timedelta(hours=24)` is defined at the top of the file. Comparing that with the issue's expected behavior ("only friends who have listened today") confirmed the window was the cause.

- **The root cause:** `get_friends_listening_now` computed its cutoff as "now minus 24 hours". That is a sliding window, so at 9am it reaches back to 9am the previous day, and an 11pm listen from the night before still passes the `>= cutoff` filter. The feature is meant to show friends who listened today, which means the cutoff has to be a fixed boundary (the start of the current day), not a moving offset from the current time. The rolling window explains the exact symptom in the report: stale listens disappear only when they are 24 hours old, which is "the same time the next day".

- **Your fix:** In `services/feed_service.py` I changed the cutoff to the start of the current UTC day: `datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)`. The rest of the query and the one-song-per-friend deduplication are unchanged. "Today" is defined in UTC, which matches how the app stores and compares all of its timestamps.

- **Your side-effect check:** After restarting the server, `GET /feed/<nova_id>/listening-now` returned `count: 0`, because the seeded listens were from the previous UTC day. This confirms stale listens are excluded. To check the other side of the boundary, I recorded a new listen as kenji through `POST /songs/<id>/listen` and re-fetched the feed, and kenji appeared, so listens from today are still included. I also confirmed that `get_activity_feed` (`GET /feed/<id>/activity`) is a separate function that never used the cutoff: it still returned 8 events before and after the change.

**Issue #3: The same song keeps showing up twice in search**

- **How you reproduced it:** `curl "http://127.0.0.1:5000/songs/search?q=Anthem"` returned `count: 3` with the same song id (`8ef89f47-...`, Crown Heights Anthem) three times. To find the pattern I compared tag counts from `flask shell` with how often each song appeared in search. Midnight Drive (0 tags) appeared 1 time, Block Party (1 tag) appeared 1 time, Harlem Renaissance (3 tags) appeared 3 times, and Crown Heights Anthem (3 tags) appeared 3 times. So duplicates equal the tag count, except that untagged songs still appear once.

- **How you found the root cause:** The match between duplicate count and tag count suggested a join against the tags association table. I followed `search` in `routes/songs.py` to `search_songs` in `services/search_service.py`. The query was `select(Song).outerjoin(song_tags, Song.id == song_tags.c.song_id).filter(...)`. The filter only looks at `Song.title` and `Song.artist`, and the tags in the output come from `song.to_dict()`, so nothing in the query uses the joined table. The outer join also explained why an untagged song still appears exactly once (an outer join keeps a row with NULLs when there is no match).

- **The root cause:** The `outerjoin(song_tags, ...)` in `search_songs` multiplies rows. A join returns one result row per matching row in `song_tags`, so a song with 3 tags produces 3 rows, a song with 1 tag produces 1, and an untagged song produces 1 row (because it is an outer join). The query uses `select(Song)` with `.scalars().all()`, which returns every row as-is and does not collapse repeated `Song` objects. Each repeated row was then serialized separately by `to_dict()`, producing identical entries. The join was never needed, since the filter only touches columns on `Song`, and the tag names come from the `Song.tags` relationship when `to_dict()` runs. That is why the duplicate count tracked the tag count exactly.

- **Your fix:** I deleted the `.outerjoin(song_tags, ...)` line from `search_songs` in `services/search_service.py`. With no join there is one row per matching song, and the tags still appear because `to_dict()` loads them itself.

- **Your side-effect check:** After restarting the server, the four searches I used to reproduce the bug returned one result each: Anthem 1 (was 3), Midnight 1, Block 1, Harlem 1 (was 3). An artist search (`q=Borough`) returned 1 result, which confirms that matching on artist still works. The Crown Heights Anthem result still lists all three tags (`rap`, `hip-hop`, `boom bap`), so removing the join did not lose tag data. The shipped tests in `tests/test_search.py` also cover single-tag, multi-tag, and untagged songs (each should appear once) and a no-match query, and they pass.

**Issue #4: Notification missing when a friend rates a song**

- **How you reproduced it:** I rated one of nova's songs as kenji: `POST /songs/cf57c010-.../rate` (Midnight Drive) with `{"user_id": <kenji>, "score": 5}`. The rating was saved and returned. Then `GET /users/<nova_id>/notifications` still showed `count: 1`, only the seeded `song_added_to_playlist` notification from darius. For the working case I used that seeded notification as the evidence, because `POST /playlists/<id>/songs` returned a 500 error in my environment (see the separate note below).

- **How you found the root cause:** The hint said to compare the working path with the missing one. The rate route is `rate` in `routes/songs.py`, which calls `rate_song` in `services/notification_service.py`. The playlist route calls `add_to_playlist` in the same file. Placing the two functions side by side, `add_to_playlist` ends with `if song.shared_by != added_by_user_id:` followed by a call to `create_notification(...)`. `rate_song` ends with `db.session.commit()` and `return rating`, and never calls `create_notification` at all. The `create_notification` docstring even lists `'song_rated'` as an example type, so the notification type was already anticipated by the code. That missing call was the specific cause.

- **The root cause:** `rate_song` saved the rating but never created a notification. Notifications in this app are not automatic: each service function has to call `create_notification` itself (as `add_to_playlist` does). `rate_song` simply never made that call, so the rating was stored and returned while the song's sharer was never told. This is a missing step rather than a wrong value, which is why there was no error and no delay, just no notification, exactly as the report described.

- **Your fix:** In `rate_song`, right after `db.session.commit()` and before `return rating`, I added the same pattern `add_to_playlist` uses: `if song.shared_by != user_id:` then `create_notification(user_id=song.shared_by, notification_type="song_rated", body=f"{rater.username} rated your song '{song.title}' {score} stars.")`. The guard prevents someone from being notified about their own rating.

- **Your side-effect check:** After restarting the server, kenji rated nova's Midnight Drive again (score 4) and nova's list grew from 1 to 2, with a new `song_rated` notification reading "kenji rated your song 'Midnight Drive' 4 stars." The seeded `song_added_to_playlist` notification was still there and the rating itself still saved (the score updated from 5 to 4). I then had nova rate her own Midnight Drive, and her notification count stayed at 2, so the self-notification guard works. That kenji re-rate showed that updating an existing rating also creates a notification. I decided this is acceptable because each submitted rating is a new event the sharer may want to see. I also wrote tests for the new behavior (see Regression Test).

**Issue #5: The last song in a playlist never shows up**

- **How you reproduced it:** `GET /playlists/<friday_energy_id>/songs` returned 6 titles. In `flask shell`, `len(playlist.songs)` was 7. I then queried the `playlist_entries` table directly and found 7 rows with positions 1 to 7. The song missing from the API response was Harlem Renaissance, the one at position 7, the highest position. The API response was exactly positions 1 to 6.

- **How you found the root cause:** The report said the missing song is always the most recently added one, and that adding another song makes the previous one reappear. That pattern means the last item of the ordered list is being dropped, not that a specific song is being filtered out. I followed `get_songs` in `routes/playlists.py` to `get_playlist_songs` in `services/playlist_service.py`. The query joins `playlist_entries` and orders by `position` ascending, which was correct (my table of positions matched it). The final line was `return [song.to_dict() for song in songs[:-1]]`, and the function's own docstring says it returns all songs in the playlist. `songs[:-1]` was the specific cause.

- **The root cause:** `get_playlist_songs` built the correct, fully ordered list of songs but then returned `songs[:-1]`. A slice ending at `-1` excludes the final element, so the song with the highest `position` was always cut off. That matches the report: the newest song has the highest position, so it is hidden. When another song is added, it takes the highest position and the previously last song moves into the returned range, so it "reappears" while the new one is hidden. The docstring promises all songs, so correct behavior is to serialize the whole list.

- **Your fix:** In `services/playlist_service.py` I changed `songs[:-1]` to `songs`, so the function returns `[song.to_dict() for song in songs]`. The query and the ordering are unchanged.

- **Your side-effect check:** After restarting the server, Friday Energy returned 7 songs in position order, ending with Harlem Renaissance. The other two playlists, Study Mode and Late Night Vibes, each returned 7 as well, and the metadata route `GET /playlists/<id>` returned the same playlist fields as before. The ordering is preserved because I did not touch the `order_by`. The shipped tests in `tests/test_playlists.py` check that all songs are returned, that they are in order, and that an empty playlist returns an empty list, and they pass.

## Additional Observation (not one of the five issues)

While reproducing Issue #5, `POST /playlists/<playlist_id>/songs` returned a 500. The server traceback ended with `sqlite3.IntegrityError: NOT NULL constraint failed: playlist_entries.position`. The failing statement was `INSERT INTO playlist_entries (playlist_id, song_id, added_at) VALUES (...)` with no `position` value, raised from `db.session.commit()` inside `add_to_playlist`. This is outside the five reported issues and I did not change it, so none of my fix commits include it. I mention it because it affected how I reproduced Issues #4 and #5: I used the seeded notification as the working case for #4 and queried `playlist_entries` directly for #5.

## Regression Test

**Test I wrote:** `tests/test_notifications.py::test_rating_notifies_song_sharer`

What it verifies: when one user rates a song shared by another user, `rate_song` creates exactly one notification for the sharer with type `song_rated`. A second test, `test_rating_own_song_does_not_notify`, confirms that rating your own song creates none.

Why it fails on the buggy code: before my fix, `rate_song` saved the rating and returned without ever calling `create_notification`, so the sharer's notification list stayed empty. To confirm, I temporarily removed the notification block from `rate_song` and ran the test. It failed with `assert 0 == 1` (zero notifications found, one expected), while the own-song test still passed. After restoring the fix, the full suite passed.

**Shipped test I also verified:** `tests/test_streaks.py::test_streak_increments_on_sunday` came with the starter repo (I did not write it). It records a Saturday listen and a Sunday listen and expects the streak to go from 1 to 2. On the old code, `update_listening_streak` only incremented in the branch `elif days_since_last == 1 and today.weekday() != 6`. On a Sunday `weekday()` is 6, so the code fell through to the reset branch. With that condition temporarily restored, the test failed with `assert 1 == 2` and the other 12 tests passed.