#!/usr/bin/python
#
# Usage:
# xspfy.py XSPF_DIR_PATH SPOTIFY_USERNAME

import spotipy
import spotipy.util
import lastfmapi
import sys

LASTFM_API_KEY        = 'f181e975265edd51e83182def6b5958a'
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

    response = spotify.search(q = query, type = 'track', offset = 0, limit = 1)

    if len(response['tracks']['items']) > 0:
        return response['tracks']['items'][0]['uri']

    return False


def spotify_playlist_create(token, username, name, public = True):
    '''
    Creates a public Spotify playlist using its API and returns its ID.
    '''
    spotify  = spotipy.Spotify(token)
    response = spotify.user_playlist_create(username, name, public = public)

    if not response or not response['id']:
        return False

    return response['id']


def spotify_playlist_add(token, username, playlist_id, tracks):
    '''
    Adds passed track URIs to the playlist specified.
    '''
    spotify  = spotipy.Spotify(token)

    # Add the first 100 tracks
    response = spotify.user_playlist_add_tracks(username, playlist_id, tracks[:100])

    if response != None:
        return False

    # A maximum of 100 tracks can be added per request, so:
    if len(tracks) > 100:
        response = spotify_playlist_add(token, username, playlist_id, tracks[100:])

    return response == None


def spotify_auth_token(username, auth_scope, client_key, client_secret, redirect_uri):
    '''
    Grabs passed scope permissions for a Spotify user.
    '''
    return spotipy.util.prompt_for_user_token(username, auth_scope, client_key, client_secret, redirect_uri)


# def spotify_playlist(filepath, delimiter = '\t'):
#     '''
#     Gets a text file and prints out a Spotify playlist to copy and paste.
#     '''
#     reader = csv.reader(open(filepath), delimiter = delimiter)

#     for line in reader:
#         # Skip file header
#         if line[0].lower() == 'track':
#             continue

#         track  = line[0]
#         artist = line[1]
#         uri    = spotify_uri(artist, track)

#         if uri:
#             print uri
#         else:
#             print 'NOT FOUND: %s - %s' % (track, artist)


def lastfm_playlists(username):
    '''
    Return an array of Last.fm playlist IDs/Titles belong to the passed username.
    '''
    lastfm    = lastfmapi.LastFmApi(LASTFM_API_KEY)
    response  = lastfm.user_getplaylists(user = username)

    if not response or len(response['playlists']['playlist']) < 1:
        return False

    playlists = []

    for playlist in response['playlists']['playlist']:
        playlists.extend([{
            'id':    playlist['id'],
            'title': playlist['title']
        }])

    return playlists


def lastfm_playlist_tracks(pl_id):
    '''
    Gets playlist tracks using by Last.fm playlist ID
    '''
    lastfm   = lastfmapi.LastFmApi(LASTFM_API_KEY)
    response = lastfm.playlist_fetch(playlistURL = 'lastfm://playlist/' + str(pl_id))

    if not response or len(response['playlist']['trackList']['track']) < 1:
        return False

    tracks = []

    for track in response['playlist']['trackList']['track']:
        tracks.extend([{
            'title':  track['title'],
            'album':  track['album'],
            'artist': track['creator'],
        }])

    return tracks


def main():
    # -------------------------------------------------------------------------
    # Check args, init
    # -------------------------------------------------------------------------
    if len(sys.argv) < 3:
        sys.exit('\nUSAGE: laspotipy.py LASTFM_USERNAME SPOTIFY_USERNAME\n')
    else:
        lastfm_user  = sys.argv[1]
        spotify_user = sys.argv[2].lower()

    # Introduce
    print '''

    Laspotipy is a utility to migrate your (or others) Last.fm playlists to your
    Spotify account where you can ACTUALLY play them, collaborate on them with
    your friends, etc.

    Unlike similar tools/services Laspotipy needs no manual export of playlists,
    no manual uploading, no manual nothing! Plus it implements much more precise
    algorithm of finding Spotify tracks.

    It first conncects to Last.fm API and fetches the playlists found for the
    specified user. No authorization is required and so you can add other user
    playlists to your Spotify account.

    On the other hand, you need to authorize Laspotipy to access to your Spotify
    account in order to be able to create playlists. After processing Last.fm playlists
    and the tracks, you will be presented with a new page opened in your browser. You
    need to login to Spotify service (if not logged in) and grant the required permissions
    to Laspotipy. If granted, you will be redirected to a new URL (sepehr.github.com/laspotipy),
    copy the whole URL and paste it to Laspotipy CLI application where it waits and waits
    for you, the lord, to be blessed by the permissions.

    OK, no more bullshit. Have fun, and listen to good music :)


    P.S. Find my music profiles at:
    http://last.fm/user/lajevardi
    http://play.spotify.com/user/sepehrlajevardi

    '''

    # Remove this, seriously!
    raw_input('Press any key to continue...')

    # -------------------------------------------------------------------------
    # Get Last.fm playlists
    # -------------------------------------------------------------------------
    spotify_pls = []
    lastfm_pls  = lastfm_playlists(lastfm_user)
    # lastfm_pls = lastfm_pls[1:2] # DEBUG

    if not lastfm_pls:
        sys.exit('[ERROR] Could not fetch last.fm playlists, is there any?')

    print '\nConnecting to Last.fm API endpoint...'
    print 'Found %d playlists for user: %s' % (len(lastfm_pls), lastfm_user)

    # -------------------------------------------------------------------------
    # Process each track to find Spotify's equivalent URI
    # -------------------------------------------------------------------------
    for pl in lastfm_pls:
        print '\nProcessing "%s"...' % pl['title']

        tracks = lastfm_playlist_tracks(pl['id'])

        if not tracks:
            print '[ERROR] Could not fetch tracks for this playlist, is there any? Skipping...'
            continue

        print 'Found %d tracks in the playlist:' % len(tracks)

        # Process each track and build spotify_pl playlist
        failed     = 0
        spotify_pl = {
            'title':  pl['title'],
            'tracks': [],
            'failed': []
        }

        for track in tracks:
            uri = spotify_uri(track['artist'], track['title'], track['album'])
            print '\t"%s - %s"' % (track['artist'][:40], track['title'][:40])

            if uri:
                print '\t[FOUND] %s\n' % uri
                spotify_pl['tracks'].extend([uri])

            else:
                print '\t[FAILED]\n'
                spotify_pl['failed'].extend(['%s - %s' % (track['artist'], track['title'])])
                failed += 1

        spotify_pls.extend([spotify_pl])
        print '%d tracks failed to be found on Spotify. Failures will be logged to file.' % failed

    # -------------------------------------------------------------------------
    # Build Spotify playlists
    # -------------------------------------------------------------------------
    print '\n\nConnecting to Spotify API endpoint, authorizing as "%s"...' % spotify_user

    # Authorize user
    token = spotify_auth_token(spotify_user, SPOTIFY_AUTH_SCOPE, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI)

    for pl in spotify_pls:
        print '\n\tCreating Spotify playlist with %d found tracks: "%s"' % (len(pl['tracks']), pl['title'])

        pl_id = spotify_playlist_create(token, spotify_user, pl['title'])
        if not pl_id:
            print '\t[ERROR] Could not create Spotify playlist. Skipping...'
            continue

        success = spotify_playlist_add(token, spotify_user, pl_id, pl['tracks'])
        if not success:
            print '\t[ERROR] Could not add tracks to the playlist. Please make sure to REMOVE the playlist manually.'
            continue

        # Logging failures
        if len(pl['failed']):
            fp = file('%s.failed.txt' % pl['title'], 'w+')
            fp.write('\n'.join(pl['failed']))
            print '\t[LOGGED]  %s.failed.txt (%d entries)' % (pl['title'], len(pl['failed']))

        print '\t[SUCCESS] Enjoy!'
    print


if __name__ == '__main__':
    main()
