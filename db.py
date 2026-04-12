"""
Database setup and seed data for Post Gal.
SQLite database with tables for users, events, and community board posts.
"""

import sqlite3
import os
import hashlib
import secrets
import json
from datetime import datetime, timedelta
import random

DB_PATH = os.path.join(os.path.dirname(__file__), "postgal.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return salt, hashed.hex()


def verify_password(password, salt, hashed):
    _, check = hash_password(password, salt)
    return check == hashed


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            display_name TEXT NOT NULL,
            bio TEXT DEFAULT '',
            role TEXT NOT NULL CHECK(role IN ('artist', 'host', 'both')),
            art_types TEXT DEFAULT '[]',
            neighborhood TEXT DEFAULT '',
            city TEXT DEFAULT 'San Francisco',
            space_description TEXT DEFAULT '',
            capacity INTEGER DEFAULT 0,
            profile_image TEXT DEFAULT '',
            website TEXT DEFAULT '',
            instagram TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            event_type TEXT NOT NULL CHECK(event_type IN (
                'house_show', 'open_studio', 'gallery', 'jam_session',
                'residency', 'workshop', 'skill_swap', 'meetup', 'other'
            )),
            host_id INTEGER NOT NULL,
            artist_ids TEXT DEFAULT '[]',
            date TEXT NOT NULL,
            time_start TEXT DEFAULT '',
            time_end TEXT DEFAULT '',
            location_name TEXT DEFAULT '',
            neighborhood TEXT DEFAULT '',
            city TEXT DEFAULT 'San Francisco',
            address TEXT DEFAULT '',
            capacity INTEGER DEFAULT 0,
            rsvp_count INTEGER DEFAULT 0,
            is_free INTEGER DEFAULT 1,
            price TEXT DEFAULT '',
            image TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            status TEXT DEFAULT 'upcoming' CHECK(status IN ('upcoming', 'past', 'cancelled')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (host_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS rsvps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(event_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            body TEXT DEFAULT '',
            post_type TEXT NOT NULL CHECK(post_type IN (
                'looking_for_venue', 'looking_for_artist', 'collab',
                'skill_swap', 'gear', 'general'
            )),
            tags TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()

    # Check if already seeded
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count > 0:
        conn.close()
        return

    # --- USERS ---
    users = [
        {
            "username": "mara_luna",
            "email": "mara@example.com",
            "display_name": "[Demo] Mara Luna",
            "bio": "Muralist and printmaker. Born in the Mission, paint everywhere. Large-scale work about migration, memory, and the ocean.",
            "role": "artist",
            "art_types": json.dumps(["murals", "printmaking", "installation"]),
            "neighborhood": "Mission District",
            "instagram": "@maraluna.art",
        },
        {
            "username": "devonte_k",
            "email": "devonte@example.com",
            "display_name": "[Demo] Devonte K.",
            "bio": "Jazz keys + electronic producer. I play every Tuesday somewhere in Oakland. Let's make it your spot.",
            "role": "artist",
            "art_types": json.dumps(["live music", "electronic", "jazz"]),
            "neighborhood": "West Oakland",
            "city": "Oakland",
            "instagram": "@devonte.keys",
        },
        {
            "username": "sage_house",
            "email": "sage@example.com",
            "display_name": "[Demo] Sage",
            "bio": "I have a backyard in Bernal with a covered patio, string lights, and room for ~40 people. Love hosting live music and open mics.",
            "role": "host",
            "neighborhood": "Bernal Heights",
            "space_description": "Covered backyard patio with PA system, string lights, fire pit. Quiet street.",
            "capacity": 40,
        },
        {
            "username": "tommy_chen",
            "email": "tommy@example.com",
            "display_name": "[Demo] Tommy Chen",
            "bio": "Photographer and zine maker. Document the Bay's underground. Run a small distro out of my garage.",
            "role": "both",
            "art_types": json.dumps(["photography", "zines", "printmaking"]),
            "neighborhood": "Sunset District",
            "space_description": "Garage space fits ~20 for zine fairs, screenings, small shows.",
            "capacity": 20,
            "instagram": "@tommy.chen.foto",
        },
        {
            "username": "rio_waters",
            "email": "rio@example.com",
            "display_name": "[Demo] Rio Waters",
            "bio": "Poet and spoken word. Performing since 16. Words about Black joy, queerness, and this city changing under our feet.",
            "role": "artist",
            "art_types": json.dumps(["spoken word", "poetry", "performance"]),
            "neighborhood": "Fillmore",
            "instagram": "@rio.waters",
        },
        {
            "username": "nina_jade",
            "email": "nina@example.com",
            "display_name": "[Demo] Nina Jade",
            "bio": "Ceramicist and community organizer. I teach free wheel-throwing workshops in my studio on weekends.",
            "role": "both",
            "art_types": json.dumps(["ceramics", "sculpture", "workshops"]),
            "neighborhood": "Dogpatch",
            "space_description": "Ceramics studio with 4 wheels, kiln, and seating for 12. Natural light.",
            "capacity": 12,
            "instagram": "@nina.jade.clay",
        },
        {
            "username": "eli_park",
            "email": "eli@example.com",
            "display_name": "[Demo] Eli Park",
            "bio": "Living room concert host. I book 2-3 shows a month â acoustic, folk, experimental. BYOB, potluck style.",
            "role": "host",
            "neighborhood": "Inner Richmond",
            "space_description": "Large Victorian living room. Grand piano available. Seats ~30 on floor cushions.",
            "capacity": 30,
        },
        {
            "username": "juniper_ray",
            "email": "juniper@example.com",
            "display_name": "[Demo] Juniper Ray",
            "bio": "Multi-instrumentalist (guitar/banjo/fiddle). Play old-time, bluegrass, and weird folk. Always looking for porch jams.",
            "role": "artist",
            "art_types": json.dumps(["live music", "folk", "bluegrass"]),
            "neighborhood": "Temescal",
            "city": "Oakland",
            "instagram": "@juniperray.music",
        },
        {
            "username": "casa_del_sol",
            "email": "casa@example.com",
            "display_name": "[Demo] Casa del Sol",
            "bio": "Artist collective house in the Mission. We host monthly art nights â painting, music, food, community. Everyone welcome.",
            "role": "host",
            "neighborhood": "Mission District",
            "space_description": "3-story Victorian with large common room, rooftop, and basement. Full PA + projector.",
            "capacity": 60,
            "website": "casadelsol.org",
        },
        {
            "username": "aya_sato",
            "email": "aya@example.com",
            "display_name": "[Demo] Aya Sato",
            "bio": "Dancer and movement artist. Butoh, contemporary, improvisation. Looking for spaces with open floors and low ceilings.",
            "role": "artist",
            "art_types": json.dumps(["dance", "performance", "movement"]),
            "neighborhood": "SoMa",
            "instagram": "@aya.moves",
        },
    ]

    for u in users:
        salt, hashed = hash_password("demo1234")
        conn.execute("""
            INSERT INTO users (username, email, password_hash, password_salt, display_name,
                bio, role, art_types, neighborhood, city, space_description, capacity,
                instagram, website)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            u["username"], u["email"], hashed, salt, u["display_name"],
            u.get("bio", ""), u["role"], u.get("art_types", "[]"),
            u.get("neighborhood", ""), u.get("city", "San Francisco"),
            u.get("space_description", ""), u.get("capacity", 0),
            u.get("instagram", ""), u.get("website", ""),
        ))

    # --- EVENTS ---
    base_date = datetime(2026, 3, 25)
    events = [
        {
            "title": "[Demo] Backyard Sessions vol. 12",
            "description": "Monthly live music in Bernal. This month: Devonte K. (keys/electronic) + Juniper Ray (folk). Potluck â bring a dish or a drink.",
            "event_type": "house_show",
            "host_id": 3,  # Sage
            "artist_ids": json.dumps([2, 8]),
            "date": (base_date + timedelta(days=3)).strftime("%Y-%m-%d"),
            "time_start": "7:00 PM",
            "time_end": "10:00 PM",
            "location_name": "Sage's Backyard",
            "neighborhood": "Bernal Heights",
            "capacity": 40,
            "is_free": 1,
            "tags": json.dumps(["live music", "potluck", "outdoor"]),
        },
        {
            "title": "[Demo] Garage Zine Fair",
            "description": "Small zine fair in the Sunset. Bring your zines, trades welcome. Screen printing demo by Tommy Chen.",
            "event_type": "other",
            "host_id": 4,  # Tommy
            "artist_ids": json.dumps([4]),
            "date": (base_date + timedelta(days=6)).strftime("%Y-%m-%d"),
            "time_start": "12:00 PM",
            "time_end": "5:00 PM",
            "location_name": "Tommy's Garage",
            "neighborhood": "Sunset District",
            "capacity": 20,
            "is_free": 1,
            "tags": json.dumps(["zines", "printmaking", "DIY"]),
        },
        {
            "title": "[Demo] Living Room Concert: Acoustic Night",
            "description": "Intimate acoustic sets in a Victorian living room. Three performers, floor seating, candlelight. BYOB.",
            "event_type": "house_show",
            "host_id": 7,  # Eli
            "artist_ids": json.dumps([8]),
            "date": (base_date + timedelta(days=8)).strftime("%Y-%m-%d"),
            "time_start": "8:00 PM",
            "time_end": "10:30 PM",
            "location_name": "Eli's Living Room",
            "neighborhood": "Inner Richmond",
            "capacity": 30,
            "is_free": 1,
            "tags": json.dumps(["acoustic", "intimate", "BYOB"]),
        },
        {
            "title": "[Demo] Free Ceramics Workshop",
            "description": "Learn wheel-throwing basics. All materials provided. Beginners very welcome. Small group, hands-on.",
            "event_type": "workshop",
            "host_id": 6,  # Nina
            "artist_ids": json.dumps([6]),
            "date": (base_date + timedelta(days=5)).strftime("%Y-%m-%d"),
            "time_start": "10:00 AM",
            "time_end": "1:00 PM",
            "location_name": "Nina's Studio",
            "neighborhood": "Dogpatch",
            "capacity": 12,
            "is_free": 1,
            "tags": json.dumps(["ceramics", "workshop", "free", "beginners"]),
        },
        {
            "title": "[Demo] Casa del Sol: First Friday",
            "description": "Monthly art night at Casa del Sol. Live painting, DJs, open mic, and free food. All ages, all welcome.",
            "event_type": "meetup",
            "host_id": 9,  # Casa del Sol
            "artist_ids": json.dumps([1, 2, 5]),
            "date": (base_date + timedelta(days=10)).strftime("%Y-%m-%d"),
            "time_start": "6:00 PM",
            "time_end": "11:00 PM",
            "location_name": "Casa del Sol",
            "neighborhood": "Mission District",
            "capacity": 60,
            "is_free": 1,
            "tags": json.dumps(["art night", "open mic", "DJs", "all ages"]),
        },
        {
            "title": "[Demo] Movement Improvisation Jam",
            "description": "Open floor for movers, dancers, and curious bodies. No experience needed. Bring socks or bare feet.",
            "event_type": "jam_session",
            "host_id": 9,  # Casa del Sol
            "artist_ids": json.dumps([10]),
            "date": (base_date + timedelta(days=12)).strftime("%Y-%m-%d"),
            "time_start": "4:00 PM",
            "time_end": "6:00 PM",
            "location_name": "Casa del Sol â Basement",
            "neighborhood": "Mission District",
            "capacity": 20,
            "is_free": 1,
            "tags": json.dumps(["dance", "movement", "improvisation"]),
        },
        {
            "title": "[Demo] Spoken Word & Soup",
            "description": "Rio Waters hosts a night of poetry and hot soup. Open mic after featured readers. Bring a poem or just listen.",
            "event_type": "house_show",
            "host_id": 7,  # Eli
            "artist_ids": json.dumps([5]),
            "date": (base_date + timedelta(days=15)).strftime("%Y-%m-%d"),
            "time_start": "7:00 PM",
            "time_end": "9:30 PM",
            "location_name": "Eli's Living Room",
            "neighborhood": "Inner Richmond",
            "capacity": 30,
            "is_free": 1,
            "tags": json.dumps(["poetry", "spoken word", "open mic", "soup"]),
        },
        {
            "title": "[Demo] Porch Jam: Old-Time & Bluegrass",
            "description": "Bring your instrument (or just your ears) to a Temescal porch for some old-time tunes. All levels welcome.",
            "event_type": "jam_session",
            "host_id": 8,  # Juniper
            "artist_ids": json.dumps([8]),
            "date": (base_date + timedelta(days=2)).strftime("%Y-%m-%d"),
            "time_start": "3:00 PM",
            "time_end": "6:00 PM",
            "location_name": "Juniper's Porch",
            "neighborhood": "Temescal",
            "city": "Oakland",
            "capacity": 15,
            "is_free": 1,
            "tags": json.dumps(["bluegrass", "jam", "porch", "all levels"]),
        },
        {
            "title": "[Demo] Mara Luna: New Mural Unveiling",
            "description": "Come see the new mural on Balmy Alley. Mara talks about the piece, the process, and the stories behind it.",
            "event_type": "gallery",
            "host_id": 1,  # Mara
            "artist_ids": json.dumps([1]),
            "date": (base_date + timedelta(days=18)).strftime("%Y-%m-%d"),
            "time_start": "5:00 PM",
            "time_end": "7:00 PM",
            "location_name": "Balmy Alley",
            "neighborhood": "Mission District",
            "capacity": 0,
            "is_free": 1,
            "tags": json.dumps(["murals", "public art", "outdoor"]),
        },
        {
            "title": "[Demo] Skill Swap Saturday",
            "description": "Trade skills with your neighbors. Teach something, learn something. Past swaps: sourdough, screen printing, guitar basics, bike repair.",
            "event_type": "skill_swap",
            "host_id": 6,  # Nina
            "artist_ids": json.dumps([]),
            "date": (base_date + timedelta(days=20)).strftime("%Y-%m-%d"),
            "time_start": "11:00 AM",
            "time_end": "3:00 PM",
            "location_name": "Nina's Studio",
            "neighborhood": "Dogpatch",
            "capacity": 12,
            "is_free": 1,
            "tags": json.dumps(["skill swap", "community", "learning"]),
        },
    ]

    for e in events:
        conn.execute("""
            INSERT INTO events (title, description, event_type, host_id, artist_ids,
                date, time_start, time_end, location_name, neighborhood, city,
                capacity, is_free, tags, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'upcoming')
        """, (
            e["title"], e["description"], e["event_type"], e["host_id"],
            e.get("artist_ids", "[]"), e["date"], e["time_start"], e["time_end"],
            e["location_name"], e["neighborhood"], e.get("city", "San Francisco"),
            e["capacity"], e["is_free"], e.get("tags", "[]"),
        ))

    # --- COMMUNITY POSTS ---
    posts = [
        {
            "user_id": 5,
            "title": "[Demo] Looking for a venue for a poetry night (15-20 people)",
            "body": "I want to host a small poetry reading in April. Need a cozy space in SF, preferably the Mission or Fillmore. Can bring my own PA. Willing to split door if there is one.",
            "post_type": "looking_for_venue",
            "tags": json.dumps(["poetry", "small venue", "Mission", "Fillmore"]),
        },
        {
            "user_id": 3,
            "title": "[Demo] Backyard available weekends in April",
            "body": "My Bernal Heights backyard is open for events most weekends in April. Covered patio, string lights, room for 40. Reach out if you want to do something.",
            "post_type": "looking_for_artist",
            "tags": json.dumps(["venue available", "Bernal Heights", "outdoor"]),
        },
        {
            "user_id": 10,
            "title": "[Demo] Dancer looking for musicians to improvise with",
            "body": "I do butoh and contemporary movement improvisation. Looking for musicians (any genre) who want to experiment with live music + dance. No plan, just play.",
            "post_type": "collab",
            "tags": json.dumps(["dance", "music", "improvisation", "collaboration"]),
        },
        {
            "user_id": 4,
            "title": "[Demo] Free screen printing intro â trade for photos?",
            "body": "I'll teach you screen printing basics in exchange for headshots or event photos. My garage in the Sunset. Weekends work best.",
            "post_type": "skill_swap",
            "tags": json.dumps(["screen printing", "photography", "trade", "Sunset"]),
        },
        {
            "user_id": 8,
            "title": "[Demo] Banjo for loan â anyone need one?",
            "body": "I have an extra open-back banjo that's just sitting around. Happy to loan it to someone who wants to learn. Temescal/Oakland pickup.",
            "post_type": "gear",
            "tags": json.dumps(["banjo", "instrument", "loan", "Oakland"]),
        },
    ]

    for p in posts:
        conn.execute("""
            INSERT INTO posts (user_id, title, body, post_type, tags)
            VALUES (?, ?, ?, ?, ?)
        """, (p["user_id"], p["title"], p["body"], p["post_type"], p["tags"]))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    seed_db()
    print("Database initialized and seeded.")
