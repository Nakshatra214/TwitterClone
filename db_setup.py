import os
import sqlite3

# Delete existing database if it exists
db_path = 'app/twitter_clone.db'
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Deleted existing database at {db_path}")

# Create a new database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create tables
cursor.execute('''
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(128),
    bio VARCHAR(500),
    location VARCHAR(100),
    website VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    profile_image VARCHAR(20) DEFAULT 'default.jpg' NOT NULL
)
''')

cursor.execute('''
CREATE TABLE followers (
    follower_id INTEGER,
    followed_id INTEGER,
    PRIMARY KEY (follower_id, followed_id),
    FOREIGN KEY (follower_id) REFERENCES user (id),
    FOREIGN KEY (followed_id) REFERENCES user (id)
)
''')

cursor.execute('''
CREATE TABLE tweet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content VARCHAR(280) NOT NULL,
    image VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user (id)
)
''')

cursor.execute('''
CREATE TABLE retweet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    tweet_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user (id),
    FOREIGN KEY (tweet_id) REFERENCES tweet (id)
)
''')

cursor.execute('''
CREATE TABLE like (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    tweet_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user (id),
    FOREIGN KEY (tweet_id) REFERENCES tweet (id)
)
''')

conn.commit()
conn.close()

print("Database created successfully with proper schema") 