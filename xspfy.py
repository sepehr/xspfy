#!/usr/bin/env python
#
# Usage:
# xspfy.py XSPF_DIR_PATH SPOTIFY_USERNAME

import xspfparser
import spotipy
import spotipy.util
import urllib
import glob
import sys
import os

SPOTIFY_CLIENT_ID     = '6508015df04044ffa68efaa4cc4ac8c3'
SPOTIFY_CLIENT_SECRET = '6186195c2bf34bd6a2caf05d76f157fc'
SPOTIFY_AUTH_SCOPE    = 'playlist-modify-public playlist-modify-private'
SPOTIFY_REDIRECT_URI  = 'https://sepehr.github.io/laspotipy'

def spotify_uri(artist, track, album = False):
    '''
    Returns spotify uri by artist and track names using Spotify Web API.
    '''
    spotify = spotipy.Spotify()

    if album:
        query = 'artist:%s album:%s %s' % (artist, album, track)
    else:
        query = 'artist:%s %s' % (artist, track)

    try:
        response = spotify.search(q = query, type = 'track', offset = 0, limit = 1)

        if len(response['tracks']['items']) > 0:
            return response['tracks']['items'][0]['uri']

        return False
    except:
        return False


def spotify_playlist_create(token, username, name, public = True):
    '''
    Creates a public Spotify playlist using its API and returns its ID.
    '''
    spotify  = spotipy.Spotify(token)

    try:
        response = spotify.user_playlist_create(username, name, public = public)

        if not response or not response['id']:
            return False

        return response['id']
    except:
        return False


def spotify_playlist_add(token, username, playlist_id, tracks):
    '''
    Adds passed track URIs to the playlist specified.
    '''
    spotify = spotipy.Spotify(token)

    # Add the first 100 tracks
    try:
        response = spotify.user_playlist_add_tracks(username, playlist_id, tracks[:100])

        if not response['snapshot_id']:
            return False

        # A maximum of 100 tracks can be added per request, so:
        if len(tracks) > 100:
            response = spotify_playlist_add(token, username, playlist_id, tracks[100:])

        return response.get('snapshot_id', False)
    except:
        return False


def spotify_auth_token(username, auth_scope, client_key, client_secret, redirect_uri):
    '''
    Grabs passed scope permissions for a Spotify user.
    '''
    return spotipy.util.prompt_for_user_token(username, auth_scope, client_key, client_secret, redirect_uri)


def xspf_playlist_paths(path):
    '''
    Reads a path and scans found XSPF playlists. Returns an array of XSPF paths.
    '''
    if os.path.isdir(path):
        return glob.glob(path + '/*.xspf')

    return [path]


def xspf_parse(path):
    '''
    Parse a single XSPF filepath into an array of ['artist', 'track'].
    '''
    pl = xspfparser.parse(path)

    if pl.bozo:
        return False

    return pl.playlist


def main():
    # -------------------------------------------------------------------------
    # Check args, init
    # -------------------------------------------------------------------------
    if len(sys.argv) < 3:
        sys.exit('\nUSAGE: xspfy.py XSPF_PATH SPOTIFY_USERNAME\n')
    else:
        xspf_path    = sys.argv[1]
        spotify_user = sys.argv[2].lower()

    # Introduce
    print '''

    XSPFy is a utility to migrate your [lastfm-exported] XSPF playlists to your
    Spotify account where you can ACTUALLY play them, collaborate on them with
    your friends, etc.

    You need to authorize XSPFy to access to your Spotify account in order to be
    able to create playlists. After processing XSPF playlists you will be presented with a
    new page opened in your browser. You need to login to Spotify service (if not logged in)
    and grant the required permissions to XSPFy. If granted, you will be redirected to a new
    URL (sepehr.github.com/laspotipy), copy the whole URL and paste it to XSPFy CLI application
    where it waits and waits for you, the lord, to be blessed by the permissions.

    OK, no more bullshit. Have fun, and listen to good music :)

    P.S. Find my music profiles at:
    http://last.fm/user/lajevardi
    http://play.spotify.com/user/sepehrlajevardi

    '''

    # Remove this, seriously!
    raw_input('Press any key to continue...')

    spotify_pls = []
    xspf_paths  = xspf_playlist_paths(xspf_path)

    if not xspf_paths:
        sys.exit('[ERROR] Could not find any XSPF playlists, is there any?')

    print 'Found %d XSPF playlist(s)' % len(xspf_paths)

    print '\nConnecting to Spotify API endpoint, authorizing as "%s"...' % spotify_user

    token = spotify_auth_token(spotify_user, SPOTIFY_AUTH_SCOPE, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI)

    for xspf_path in xspf_paths:
        print '\nProcessing "%s"...' % xspf_path

        pl = xspf_parse(xspf_path)

        if not pl.track:
            print '[ERROR] Could not fetch tracks for this playlist, is there any? Skipping...'
            continue

        failed = count = 0
        pl_len = len(pl.track)
        spotify_pl = {
            'title':  pl.title,
            'tracks': []
        }

        print 'Found %d tracks in the playlist:' % pl_len

        for track in pl.track:
            uri = spotify_uri(track.creator, track.title)

            count += 1
            print '\t%d/%d: "%s - %s"' % (count, pl_len, track.creator[:40], track.title[:40])

            if uri:
                print '\t[FOUND] %s\n' % uri
                spotify_pl['tracks'].extend([uri])

            else:
                print '\t[FAILED]\n'
                failed += 1

        spotify_pls.extend([spotify_pl])

        print '%d tracks not found on Spotify.' % failed

        print 'Creating Spotify playlist with %d found tracks: "%s"' % (len(spotify_pl['tracks']), spotify_pl['title'])

        pl_id = spotify_playlist_create(token, spotify_user, spotify_pl['title'])
        if not pl_id:
            print '[ERROR] Could not create Spotify playlist. Skipping...'
            continue

        success = spotify_playlist_add(token, spotify_user, pl_id, spotify_pl['tracks'])
        if not success:
            print '[ERROR] Could not add tracks to the playlist. Please make sure to REMOVE the playlist manually.'
            continue

        print '[SUCCESS] Enjoy!'


if __name__ == '__main__':
    main()
