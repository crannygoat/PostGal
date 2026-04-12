"""
Post Gal — Bay Area artist/host community platform.
Tornado web server with REST API + static file serving.
"""

import tornado.ioloop
import tornado.web
import tornado.escape
import json
import os
import hashlib
import secrets
from datetime import datetime

from db import get_db, init_db, seed_db, hash_password, verify_password

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")

# Simple token store (in-memory for this version)
TOKENS = {}


def make_token(user_id):
    token = secrets.token_hex(32)
    TOKENS[token] = user_id
    return token


def get_user_from_token(handler):
    auth = handler.request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        return TOKENS.get(token)
    return None


class BaseHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

    def write_json(self, data, status=200):
        self.set_status(status)
        self.write(json.dumps(data, default=str))

    def get_current_user_id(self):
        return get_user_from_token(self)


# ─── AUTH ───

class SignupHandler(BaseHandler):
    def post(self):
        data = tornado.escape.json_decode(self.request.body)
        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "")
        display_name = data.get("display_name", "").strip()
        role = data.get("role", "artist")

        if not all([username, email, password, display_name]):
            return self.write_json({"error": "All fields required"}, 400)

        salt, hashed = hash_password(password)
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, email, password_hash, password_salt, display_name, role) VALUES (?, ?, ?, ?, ?, ?)",
                (username, email, hashed, salt, display_name, role),
            )
            db.commit()
            user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            token = make_token(user_id)
            self.write_json({"token": token, "user_id": user_id, "username": username})
        except Exception as e:
            self.write_json({"error": "Username or email already taken"}, 400)
        finally:
            db.close()


class LoginHandler(BaseHandler):
    def post(self):
        data = tornado.escape.json_decode(self.request.body)
        username = data.get("username", "").strip()
        password = data.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (username, username),
        ).fetchone()
        db.close()

        if user and verify_password(password, user["password_salt"], user["password_hash"]):
            token = make_token(user["id"])
            self.write_json({
                "token": token,
                "user_id": user["id"],
                "username": user["username"],
                "display_name": user["display_name"],
                "role": user["role"],
            })
        else:
            self.write_json({"error": "Invalid credentials"}, 401)


# ─── USERS / PROFILES ───

class UsersHandler(BaseHandler):
    def get(self):
        db = get_db()
        role = self.get_argument("role", None)
        neighborhood = self.get_argument("neighborhood", None)
        search = self.get_argument("q", None)

        query = "SELECT id, username, display_name, bio, role, art_types, neighborhood, city, space_description, capacity, profile_image, website, instagram FROM users WHERE 1=1"
        params = []

        if role:
            if role == "host":
                query += " AND role IN ('host', 'both')"
            elif role == "artist":
                query += " AND role IN ('artist', 'both')"
            else:
                query += " AND role = ?"
                params.append(role)

        if neighborhood:
            query += " AND neighborhood = ?"
            params.append(neighborhood)

        if search:
            query += " AND (display_name LIKE ? OR bio LIKE ? OR art_types LIKE ? OR neighborhood LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s, s])

        query += " ORDER BY created_at DESC"
        users = [dict(row) for row in db.execute(query, params).fetchall()]
        db.close()
        self.write_json(users)


class UserHandler(BaseHandler):
    def get(self, user_id):
        db = get_db()
        user = db.execute(
            "SELECT id, username, display_name, bio, role, art_types, neighborhood, city, space_description, capacity, profile_image, website, instagram, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        db.close()
        if user:
            self.write_json(dict(user))
        else:
            self.write_json({"error": "User not found"}, 404)

    def put(self, user_id):
        uid = self.get_current_user_id()
        if uid != int(user_id):
            return self.write_json({"error": "Unauthorized"}, 403)

        data = tornado.escape.json_decode(self.request.body)
        allowed = ["display_name", "bio", "role", "art_types", "neighborhood", "city",
                    "space_description", "capacity", "website", "instagram"]
        sets = []
        params = []
        for k in allowed:
            if k in data:
                sets.append(f"{k} = ?")
                v = data[k]
                if isinstance(v, (list, dict)):
                    v = json.dumps(v)
                params.append(v)

        if not sets:
            return self.write_json({"error": "Nothing to update"}, 400)

        params.append(user_id)
        db = get_db()
        db.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = ?", params)
        db.commit()
        db.close()
        self.write_json({"ok": True})


# ─── EVENTS ───

class EventsHandler(BaseHandler):
    def get(self):
        db = get_db()
        month = self.get_argument("month", None)
        event_type = self.get_argument("type", None)
        neighborhood = self.get_argument("neighborhood", None)
        search = self.get_argument("q", None)

        query = """
            SELECT e.*, u.display_name as host_name, u.username as host_username
            FROM events e
            JOIN users u ON e.host_id = u.id
            WHERE 1=1
        """
        params = []

        if month:
            query += " AND e.date LIKE ?"
            params.append(f"{month}%")

        if event_type:
            query += " AND e.event_type = ?"
            params.append(event_type)

        if neighborhood:
            query += " AND e.neighborhood = ?"
            params.append(neighborhood)

        if search:
            query += " AND (e.title LIKE ? OR e.description LIKE ? OR e.tags LIKE ? OR e.neighborhood LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s, s])

        query += " ORDER BY e.date ASC, e.time_start ASC"
        events = [dict(row) for row in db.execute(query, params).fetchall()]
        db.close()
        self.write_json(events)

    def post(self):
        uid = self.get_current_user_id()
        if not uid:
            return self.write_json({"error": "Login required"}, 401)

        data = tornado.escape.json_decode(self.request.body)
        required = ["title", "event_type", "date"]
        if not all(data.get(k) for k in required):
            return self.write_json({"error": "Title, type, and date required"}, 400)

        db = get_db()
        db.execute("""
            INSERT INTO events (title, description, event_type, host_id, artist_ids,
                date, time_start, time_end, location_name, neighborhood, city,
                capacity, is_free, price, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["title"], data.get("description", ""), data["event_type"], uid,
            json.dumps(data.get("artist_ids", [])), data["date"],
            data.get("time_start", ""), data.get("time_end", ""),
            data.get("location_name", ""), data.get("neighborhood", ""),
            data.get("city", "San Francisco"), data.get("capacity", 0),
            data.get("is_free", 1), data.get("price", ""),
            json.dumps(data.get("tags", [])),
        ))
        db.commit()
        event_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.close()
        self.write_json({"ok": True, "event_id": event_id}, 201)


class EventHandler(BaseHandler):
    def get(self, event_id):
        db = get_db()
        event = db.execute("""
            SELECT e.*, u.display_name as host_name, u.username as host_username
            FROM events e JOIN users u ON e.host_id = u.id
            WHERE e.id = ?
        """, (event_id,)).fetchone()
        db.close()
        if event:
            self.write_json(dict(event))
        else:
            self.write_json({"error": "Event not found"}, 404)


class RsvpHandler(BaseHandler):
    def post(self, event_id):
        uid = self.get_current_user_id()
        if not uid:
            return self.write_json({"error": "Login required"}, 401)

        db = get_db()
        try:
            db.execute("INSERT INTO rsvps (event_id, user_id) VALUES (?, ?)", (event_id, uid))
            db.execute("UPDATE events SET rsvp_count = rsvp_count + 1 WHERE id = ?", (event_id,))
            db.commit()
            self.write_json({"ok": True})
        except Exception:
            self.write_json({"error": "Already RSVP'd"}, 400)
        finally:
            db.close()


# ─── COMMUNITY BOARD ───

class PostsHandler(BaseHandler):
    def get(self):
        db = get_db()
        post_type = self.get_argument("type", None)
        search = self.get_argument("q", None)

        query = """
            SELECT p.*, u.display_name as author_name, u.username as author_username
            FROM posts p JOIN users u ON p.user_id = u.id WHERE 1=1
        """
        params = []
        if post_type:
            query += " AND p.post_type = ?"
            params.append(post_type)
        if search:
            query += " AND (p.title LIKE ? OR p.body LIKE ? OR p.tags LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s])

        query += " ORDER BY p.created_at DESC"
        posts = [dict(row) for row in db.execute(query, params).fetchall()]
        db.close()
        self.write_json(posts)

    def post(self):
        uid = self.get_current_user_id()
        if not uid:
            return self.write_json({"error": "Login required"}, 401)

        data = tornado.escape.json_decode(self.request.body)
        if not data.get("title"):
            return self.write_json({"error": "Title required"}, 400)

        db = get_db()
        db.execute("""
            INSERT INTO posts (user_id, title, body, post_type, tags)
            VALUES (?, ?, ?, ?, ?)
        """, (
            uid, data["title"], data.get("body", ""),
            data.get("post_type", "general"),
            json.dumps(data.get("tags", [])),
        ))
        db.commit()
        db.close()
        self.write_json({"ok": True}, 201)


# ─── NEIGHBORHOODS HELPER ───

class NeighborhoodsHandler(BaseHandler):
    def get(self):
        db = get_db()
        hoods = db.execute(
            "SELECT DISTINCT neighborhood FROM users WHERE neighborhood != '' UNION SELECT DISTINCT neighborhood FROM events WHERE neighborhood != '' ORDER BY neighborhood"
        ).fetchall()
        db.close()
        self.write_json([row["neighborhood"] for row in hoods])


# ─── STATIC FILES ───

class IndexHandler(tornado.web.RequestHandler):
    def get(self, path=""):
        with open(os.path.join(STATIC_DIR, "index.html"), "r") as f:
            self.write(f.read())


def make_app():
    return tornado.web.Application([
        # API routes
        (r"/api/signup", SignupHandler),
        (r"/api/login", LoginHandler),
        (r"/api/users", UsersHandler),
        (r"/api/users/(\d+)", UserHandler),
        (r"/api/events", EventsHandler),
        (r"/api/events/(\d+)", EventHandler),
        (r"/api/events/(\d+)/rsvp", RsvpHandler),
        (r"/api/posts", PostsHandler),
        (r"/api/neighborhoods", NeighborhoodsHandler),
        # Static files
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": STATIC_DIR}),
        (r"/uploads/(.*)", tornado.web.StaticFileHandler, {"path": UPLOAD_DIR}),
        # SPA fallback
        (r"/(.*)", IndexHandler),
    ], debug=os.environ.get("DEBUG", "false").lower() == "true")


if __name__ == "__main__":
    init_db()
    seed_db()
    app = make_app()
    port = int(os.environ.get("PORT", 8888))
    app.listen(port)
    print(f"\n  POST GAL is running on port {port}\n")
    tornado.ioloop.IOLoop.current().start()
