from flask import Flask, redirect, render_template, request, session, url_for, make_response
from functools import wraps
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
from animus import (
    generate_aspects_description,
    generate_playlist_description,
    generate_spotify_parameters,
    generate_title,
    get_recommendations,
    create_playlist
)
import logging
import secrets
from urllib.parse import quote
import random

# Load environment variables
load_dotenv('local.env')

# Verify environment variables
client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
redirect_uri = 'http://127.0.0.1:5000/callback'  # Hardcode this instead of using env var

if not client_id or not client_secret:
    raise ValueError("Missing Spotify credentials in environment variables")

app = Flask(__name__)
app.secret_key = os.urandom(24)

SPOTIFY_SCOPES = "playlist-modify-public"

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load puns from file
with open('puns.txt', 'r') as f:
    PUNS = [line.strip() for line in f.readlines()]

def create_spotify_oauth() -> SpotifyOAuth:
    return SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SPOTIFY_SCOPES,
        open_browser=False,
        show_dialog=True,
        cache_handler=None,
        requests_timeout=30
    )

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('token_info'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    # Clear any existing session data (like previous logins)
    session.clear()
    
    # Get a random pun
    random_pun = random.choice(PUNS)
    
    # Render the index.html template with the random pun
    response = make_response(render_template('index.html', random_pun=random_pun))
    
    # Add Content Security Policy headers
    response.headers['Content-Security-Policy'] = (
        "default-src 'self' https://accounts.spotify.com; "
        "script-src 'self' https://accounts.spotify.com; "
        "style-src 'self' 'unsafe-inline' https://accounts.spotify.com; "
        "img-src 'self' data: https://accounts.spotify.com; "
        "frame-src 'self' https://accounts.spotify.com; "
        "connect-src 'self' https://accounts.spotify.com; "
        "object-src 'none'"
    )
    return response

@app.route('/login')
def login():
    try:
        if not client_id:
            raise ValueError("Client ID is missing")
            
        sp_oauth = create_spotify_oauth()
        
        # Generate state
        state = secrets.token_hex(16)
        session['oauth_state'] = state
        
        # Get auth URL with state parameter
        encoded_redirect = quote(redirect_uri, safe='')
        encoded_scope = quote(SPOTIFY_SCOPES, safe='')
        
        auth_url = (
            f"https://accounts.spotify.com/authorize"
            f"?client_id={client_id}"
            f"&response_type=code"
            f"&redirect_uri={encoded_redirect}"
            f"&scope={encoded_scope}"
            f"&state={state}"
        )
        
        logger.debug(f"Final auth URL with state: {auth_url}")
        
        # Set additional headers for Spotify auth page
        response = make_response(redirect(auth_url))
        response.headers['Referrer-Policy'] = 'no-referrer-when-downgrade'
        return response
        
    except Exception as e:
        logger.error(f"Error in login route: {str(e)}")
        if client_id:
            logger.error(f"Client ID: {client_id[:5]}... (truncated)")
        logger.error(f"Redirect URI: {redirect_uri}")
        return render_template('index.html', error="Failed to connect to Spotify. Please try again.")

@app.route('/callback')
def callback():
    try:
        sp_oauth = create_spotify_oauth()
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')

        logger.debug(f"Callback received - Code: {code}, State: {state}, Error: {error}")
        logger.debug(f"Session state: {session.get('oauth_state')}")
        
        if error:
            logger.error(f"Error returned from Spotify: {error}")
            return render_template('index.html', error=f"Authentication failed: {error}")
            
        if not code:
            logger.error("No code received from Spotify")
            return render_template('index.html', error="No authorization code received. Please try again.")
        
        if state != session.get('oauth_state'):
            logger.error(f"State mismatch. Got {state}, expected {session.get('oauth_state')}")
            return render_template('index.html', error="Invalid state parameter. Please try again.")
        
        token_info = sp_oauth.get_access_token(code, as_dict=True, check_cache=False)
        if not token_info:
            logger.error("Failed to get access token")
            return render_template('index.html', error="Failed to get access token. Please try again.")
            
        session['token_info'] = token_info
        return redirect(url_for('generate'))
        
    except Exception as e:
        logger.error(f"Error in callback route: {str(e)}")
        return render_template('index.html', error=f"Authentication error: {str(e)}")

@app.route('/generate', methods=['GET', 'POST'])
@login_required
def generate():
    if request.method == 'POST':
        target = request.form['target']
        
        try:
            # Get Spotify token
            token_info = session['token_info']
            spotify_token = token_info['access_token']
            
            # Generate playlist
            aspects_description = generate_aspects_description(target)
            playlist_description = generate_playlist_description(target, aspects_description)
            spotify_params = generate_spotify_parameters(playlist_description)
            title, description = generate_title(target, aspects_description, playlist_description)
            tracks, track_uris = get_recommendations(spotify_params, spotify_token)
            
            # Add target to Spotify description but not display description
            spotify_description = f"{description} made with animus for {target}."
            display_description = description.split('made with animus')[0]
            
            playlist_url = create_playlist(title, spotify_description, track_uris, spotify_token)
            
            if not playlist_url:
                raise Exception("Failed to create playlist")
            
            # Clean up the title
            clean_title = title.replace('animus: ', '')
                
            return render_template('result.html', 
                                playlist_url=playlist_url,
                                title=clean_title,
                                description=display_description)
        except Exception as e:
            logger.error(f"Error generating playlist: {str(e)}")
            return render_template('generate.html', error="Failed to generate playlist. Please try again.")
    
    return render_template('generate.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
