from dotenv import load_dotenv
import os
import pandas as pd
import logging

from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

import spotipy
from spotipy.oauth2 import SpotifyOAuth

logger = logging.getLogger(__name__)

def load_template(template_path: str, input_variables: list[str]) -> PromptTemplate:
    with open(template_path, 'r') as file:
        template_string = file.read()
    return PromptTemplate(template=template_string, input_variables=input_variables)


if os.getenv('FLASK_ENV') != 'production':
    load_dotenv('local.env')

anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')

llm = ChatAnthropic(
    anthropic_api_key=anthropic_api_key, # type: ignore
    model='claude-3-5-sonnet-20241022',
    temperature=0.8
)

animistic_template = load_template('animistic_template.txt', input_variables=['target'])
animistic_chain = animistic_template | llm

def generate_animistic_description(target: str) -> str:
    return animistic_chain.invoke({'target': target}).content # type: ignore

aspects_template = load_template('aspects_template.txt', input_variables=['target'])
aspects_chain = aspects_template | llm

def generate_aspects_description(target: str) -> str:
    return aspects_chain.invoke({'target': target}).content # type: ignore

description_template = load_template('description_template.txt', input_variables=['aspects', 'target'])
description_chain = description_template | llm

def generate_playlist_description(target: str, aspects: str) -> str:
    return description_chain.invoke({'aspects': aspects, 'target': target}).content # type: ignore

spotify_template = load_template('spotify_template.txt', input_variables=['target', 'description'])
spotify_chain = spotify_template | llm | JsonOutputParser()
    

def generate_spotify_parameters(description: str) -> dict:
    return spotify_chain.invoke({'description': description}, model_kwargs={'temperature': 0.2}) # type: ignore

title_template = load_template('title_template.txt', input_variables=['target', 'description', 'aspects'])
title_chain = title_template | llm | JsonOutputParser()

def generate_title(target: str, aspects: str, playlist_description: str) -> tuple[str, str]:
    response = title_chain.invoke({'target': target, 'aspects': aspects, 'description': playlist_description}) # type: ignore
    title = f"animus: {response['title']}"
    playlist_description = response['description']
    return title, playlist_description

def load_banned_artists() -> pd.DataFrame:
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'banned_artists.txt')
        logger.info(f"Loading banned artists from {file_path}")
        return pd.read_csv(file_path)
    except Exception as e:
        logger.error(f"Failed to load banned artists: {e}")
        return pd.DataFrame(columns=['uri'])

banned_artists = load_banned_artists()

def is_banned_artist(artist_uri: str) -> bool:
    return artist_uri in banned_artists['uri'].values

def filter_banned_artists(tracks: list[dict]) -> list[dict]:
    return [track for track in tracks if not is_banned_artist(track['artists'][0]['uri'])]


def get_recommendations(params: dict, spotify_token: str) -> tuple[list[dict], list[str]]:
    if not spotify_token:
        logger.error("No Spotify token provided")
        return [], []
        
    sp = spotipy.Spotify(auth=spotify_token)
    params['limit'] = 100
    params['market'] = 'US'
    try:
        response = sp.recommendations(**params)
        if not response or 'tracks' not in response:
            logger.error("No recommendations received from Spotify")
            return [], []
            
        tracks = filter_banned_artists(response['tracks'])
        if not tracks:
            logger.error("No tracks remained after filtering")
            return [], []
            
        track_uris = [track['uri'] for track in tracks if 'uri' in track]
        return tracks, track_uris
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        return [], []

def create_playlist(title: str, description: str, track_uris: list[str], spotify_token: str) -> str:
    if not spotify_token:
        logger.error("No Spotify token provided")
        return ''
        
    sp = spotipy.Spotify(auth=spotify_token)
    try:
        current_user = sp.current_user()
        if not current_user:
            logger.error("Could not get current user")
            return ''
        
        playlist = sp.user_playlist_create(
            user=current_user['id'],
            name=title,
            description=description,
            public=True
        )
        
        if playlist and 'id' in playlist:
            sp.user_playlist_add_tracks(current_user['id'], playlist['id'], track_uris)
            return playlist['external_urls']['spotify']
        
        logger.error("Failed to create playlist")
        return ''
    except Exception as e:
        logger.error(f"Error creating playlist: {str(e)}")
        return ''

if __name__ == '__main__':
    target = input('Enter a target: ')
    aspects_description = generate_aspects_description(target)
    print(aspects_description)
    playlist_description = generate_playlist_description(target, aspects_description)
    print(playlist_description)
    spotify_params = generate_spotify_parameters(playlist_description)
    print(spotify_params)
    title, description = generate_title(target, aspects_description, playlist_description)
    print(title)
    print(description)
    
    sp_oauth = SpotifyOAuth(
        client_id=os.getenv('SPOTIPY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
        redirect_uri=os.getenv('REDIRECT_URI', 'http://localhost:5000/callback'),
        scope="playlist-modify-public"
    )
    token_info = sp_oauth.get_cached_token()
    if token_info:
        spotify_token = token_info['access_token']
        tracks, track_uris = get_recommendations(spotify_params, spotify_token)
        playlist_url = create_playlist(title, description, track_uris, spotify_token)
        print(playlist_url)
    else:
        print("No Spotify token available. Please authenticate first.")