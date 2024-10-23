from dotenv import load_dotenv
import os

from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

import spotipy
from spotipy.oauth2 import SpotifyOAuth


def load_template(template_path: str, input_variables: list[str]) -> PromptTemplate:
    with open(template_path, 'r') as file:
        template_string = file.read()
    return PromptTemplate(template=template_string, input_variables=input_variables)


load_dotenv('local.env')
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')

llm = ChatAnthropic(
    anthropic_api_key=anthropic_api_key, # type: ignore
    model='claude-3-5-sonnet',
    temperature=0.8
)

animistic_template = load_template('animistic_template.txt', input_variables=['target'])
animistic_chain = animistic_template | llm

def generate_animistic_description(target: str) -> str:
    return animistic_chain.invoke({'target': target}).content # type: ignore

spotify_template = load_template('spotify_template.txt', input_variables=['target', 'description'])
spotify_chain = spotify_template | llm | JsonOutputParser()

def generate_spotify_parameters(target: str, description: str) -> dict:
    return spotify_chain.invoke({'target': target, 'description': description}) # type: ignore

title_template = load_template('title_template.txt', input_variables=['target', 'description'])
title_chain = title_template | llm | JsonOutputParser()

def generate_title(target: str, description: str) -> tuple[str, str]:
    response = title_chain.invoke({'target': target, 'description': description}) # type: ignore
    title = f"Animus: {response['title']}"
    playlist_description = response['description'] + " Made with Animus."
    return title, playlist_description

client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
redirect_uri = os.getenv('SPOTIPY_REDIRECT_URI')

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        scope="playlist-modify-public",
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        cache_path='cache.json',
    )
)

current_user = sp.current_user()

def get_recommendations(params: dict) -> tuple[list[dict], list[str]]:
    tracks = sp.recommendations(**params)
    track_uris = [track['uri'] for track in tracks['tracks']] # type: ignore
    return tracks, track_uris # type: ignore

def create_playlist(title: str, description: str, track_uris: list[str]) -> str:
    playlist = sp.user_playlist_create(
        user=current_user['id'], name=title, description=description, public=True # type: ignore
    )
    sp.user_playlist_add_tracks(current_user['id'], playlist['id'], track_uris) # type: ignore
    return playlist['external_urls']['spotify']

if __name__ == '__main__':
    target = input('Enter a target: ')
    animistic_description = generate_animistic_description(target)
    print(animistic_description)
    spotify_params = generate_spotify_parameters(target, animistic_description)
    print(spotify_params)
    title, description = generate_title(target, animistic_description)
    print(title)
    print(description)
    tracks, track_uris = get_recommendations(spotify_params)
    playlist_url = create_playlist(title, description, track_uris)
    print(playlist_url)