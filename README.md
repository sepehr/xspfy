#XSPFy

Migrates XSPF playlists to Spotify where they can grow old.

It's the ancessor of [Laspotipy](https://github.com/sepehr/laspotipy). Laspotipy does not work anymore as Last.fm's Playlist API does not work anymore.

Exported XSPF playlists can be imported using this utility instead.

###Usage
`python xspfy.py XSPF_PATH SPOTIFY_USERNAME`

###Requirements
- spotipy
- requests

###Installation
    pip install requests spotipy
    git clone https://github.com/sepehr/xspfy.git
    chmod +x ./xspfy/xspfy.py
