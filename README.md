#XSPFy

Migrates XSPF playlists to Spotify where they can grow old.

It's the ancessor of [Laspotipy](https://github.com/sepehr/laspotipy). Laspotipy does not work anymore as Last.fm's Playlist API does not work anymore. Exported XSPF playlists can be imported using this utility instead.

As of the new fuckin lastfm beta, playlists can be found on the old website:  
https://www.last.fm/user/lajevardi/library/playlists  

The built-in export feature does not work anymore as the Playlists API is gone. Consider using a workaround to scrape and save data locally:  
http://jsbin.com/vivucuceco/1/edit?html,output

Convert CSV files to XSPF playlists:  
https://github.com/kevlened/csvToXspf

To export your Spotify playlists:  
https://rawgit.com/watsonbox/exportify/master/exportify.html

###Usage
`python xspfy.py XSPF_PATH SPOTIFY_USERNAME`

###Screenshot
![XSPFy screenshot](https://hostr.co/file/AsJX2zukaVkt/xspfy.png)

###Installation
    pip install requests spotipy
    git clone https://github.com/sepehr/xspfy.git
    chmod +x ./xspfy/xspfy.py

