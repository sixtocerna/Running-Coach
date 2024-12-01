import sqlite3
import datetime
import requests
import os
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
redirect_uri = os.getenv('REDIRECT_URI')

class TokenManager:
    def __init__(self, db_file, client_id, client_secret):
        self.db_file = db_file
        self.client_id = client_id
        self.client_secret = client_secret
        self.create_token_table()

    def create_token_table(self):
        """Create the token table if it doesn't exist."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY,
            access_token TEXT NOT NULL,
            access_token_expires_at DATETIME NOT NULL,
            refresh_token TEXT NOT NULL
        )
        ''')

        conn.commit()
        conn.close()

    def _get_tokens_from_db(self):
        """Fetch both access and refresh tokens from the database."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute("SELECT access_token, access_token_expires_at, refresh_token FROM tokens WHERE id = 1")
        token_data = cursor.fetchone()

        conn.close()

        if token_data:
            access_token, access_token_expires_at_str, refresh_token = token_data
            access_token_expires_at = datetime.datetime.strptime(access_token_expires_at_str, '%Y-%m-%d %H:%M:%S+00:00').replace(tzinfo=datetime.timezone.utc)
            return access_token, access_token_expires_at, refresh_token
        return None, None, None

    def _store_tokens_in_db(self, access_token, access_token_expires_at, refresh_token):
        """Store both access token and refresh token along with expiration time in the database."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute("INSERT OR REPLACE INTO tokens (id, access_token, access_token_expires_at, refresh_token) VALUES (1, ?, ?, ?)",
                       (access_token, access_token_expires_at.strftime('%Y-%m-%d %H:%M:%S')+'+00:00', refresh_token))

        conn.commit()
        conn.close()

    def _is_token_expired(self, expires_at):
        """Check if the access token has expired."""
        # Get the current UTC time

        now_utc = datetime.datetime.now(datetime.timezone.utc)

        return now_utc >= expires_at

    def _get_access_token(self):
        """Get the current access token, refreshing it if necessary."""
        access_token, access_token_expires_at, refresh_token = self._get_tokens_from_db()

        if access_token and not self._is_token_expired(access_token_expires_at):
            return access_token

        self._refresh_access_token(refresh_token)
        access_token, _, _ = self._get_tokens_from_db()
        return access_token

    def _refresh_access_token(self, refresh_token):
        """Refresh the access token using the refresh token."""
        if not refresh_token:
            raise ValueError("No refresh token available")

        # Send the request to refresh the token
        token_url = f"https://api.wahooligan.com/oauth/token?client_secret={self.client_secret}&client_id={self.client_id}&grant_type=refresh_token&refresh_token={refresh_token}"
        response = requests.post(token_url)

        if response.status_code != 200:
            raise Exception(f"Failed to refresh token: {response.status_code} {response.text}")

        # Parse the response and store the new access token
        response_data = response.json()
        access_token = response_data['access_token']
        refresh_token = response_data['refresh_token']  # Use the old refresh token if not returned
        expires_in = response_data['expires_in'] 
        created_at = response_data['created_at']

        access_token_expires_at = datetime.datetime.fromtimestamp(created_at, tz=datetime.timezone.utc) + datetime.timedelta(seconds=expires_in)

        # Store the new access token and refresh token
        self._store_tokens_in_db(access_token, access_token_expires_at, refresh_token)

        print("Access token refreshed successfully!")

# Usage example:
# Initialize with your credentials and tokens
token_manager = TokenManager(
    db_file="db.sqlite3",  # SQLite database file
    client_id=client_id,
    client_secret=client_secret
)

# Get the current access token (it will refresh automatically if expired)
access_token = token_manager._get_access_token()
print(f"Access token: {access_token}")
