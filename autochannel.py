import spotipy
import os
import re
import pafy
import requests
import pandas as pd
import numpy as np
import json
from spotipy.oauth2 import SpotifyClientCredentials
from youtube_functions import youtube_search, get_video_list, get_authenticated_service, upload, get_result_number
from pydub import AudioSegment
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from time import sleep
from PIL import Image, ImageFont, ImageDraw

with open('keys.json') as f:
    keys = json.load(f)
    YOUTUBE_API_KEY = keys['YOUTUBE_API_KEY']
    SPOTIFY_ID = keys['SPOTIFY_ID']
    SPOTIFY_SECRET = keys['SPOTIFY_SECRET']
    LASTFM_KEY = keys['LASTFM_KEY']
                     
class VideoMaker:
    def __init__(self, title, artists, playlist):

        self.playlist = playlist
        self.title = re.sub(' - .+$', '', title)
        self.artists = artists
        self.title_complete = ' - '.join([self.title, ', '.join([artist for artist in self.artists
                                                                 if artist.lower() not in self.title.lower()])])
        self.title_simple = re.findall('[^([]+', self.title)[0].strip().lower()
        self.title_path = '_'.join(self.title_simple.split(' '))
        self.step = 'start'
        self.files = {'url':None, 'm4a':None, 'wav':None, 'wav_speed':None, 'wav_pitch_up':None,
                      'png_chipmunks':None, 'png_nightcore':None, 'mp4_chipmunks':None,
                      'mp4_nightcore':None}
    
    def create_file(self, extension, folder='temp/'):
        return folder + self.title_path + extension

    def find_song_on_youtube(self):
        q = ' '.join(re.findall('\w+', self.title_complete)) + ' lyrics'
        search = youtube_search(q)[1]
        video = search[0]
        video_title = video['snippet']['title'].lower()
        if self.title_simple.lower() not in video_title.lower()\
        or any(word in video_title for word in ['reaction', 'trailer']):
            return 'song not found'
        self.files['url'] = "www.youtube.com/watch?v=" + video['id']['videoId']

    def download_song(self):
        video = pafy.new(self.files['url'])
        audiostreams = [stream for stream in video.audiostreams if stream.extension == 'm4a']
        self.files['m4a'] = audiostreams[0].download(filepath=self.create_file('.m4a'), quiet=True)   

    def convert(self):
        sound = AudioSegment.from_file(self.files['m4a'])
        sound.export(self.create_file('.wav'), format="wav")
        self.files['wav'] = self.create_file('.wav')

    def pitch_up_song(self, pitch=7):
        os.chdir('rubberband')
        os.system('rubberband -t 1.0 -p {}.0 {} {}'.format(pitch, self.create_file('.wav', '../temp/'),
                  self.create_file('_pitch_up.wav', '../temp/')))
        os.chdir('..')
        self.files['wav_pitch_up'] = self.create_file('_pitch_up.wav')
        
    def pitch_down_song(self, pitch=-4):
        os.chdir('rubberband')
        os.system('rubberband -t 1.0 -p {}.0 {} {}'.format(pitch, self.create_file('.wav', '../temp/'),
                  self.create_file('_pitch_down.wav', '../temp/')))
        os.chdir('..')
        self.files['wav_pitch_down'] = self.create_file('_pitch_down.wav')

    def speed_up_song(self, octaves=0.35):
        sound = AudioSegment.from_file(self.files['wav'])
        new_sample_rate = int(sound.frame_rate * (2.0 ** octaves))
        hipitch_sound = sound._spawn(sound.raw_data, overrides={'frame_rate': new_sample_rate})
        hipitch_sound = hipitch_sound.set_frame_rate(44100)
        hipitch_sound.export(self.create_file('_speed.wav'), format="wav")
        self.files['wav_speed'] = self.create_file('_speed.wav')

    def create_background(self, effect):
        title = self.title_simple.center(10, ' ')
        char_size = {' ': 40, '!': 52, '$': 100, '/': 100,  ':': 48, '?': 90, '-': 65, "'": 48, '0': 100,
                     '1': 100, '2': 100, '3': 100, '4': 100, '5': 100, '6': 100, '7': 100, '8': 100, '&':100,
                     '9': 100, 'a': 100, 'b': 100, 'c': 95, 'd': 100, 'e': 92, 'f': 88, 'g': 97, 'h': 105,
                     'i': 47, 'j': 65, 'k': 103, 'l': 85, 'm': 135, 'n': 105, 'o': 100, 'p': 95, 'q': 100,
                     'r': 100, 's': 90, 't': 92, 'u': 100, 'v': 95, 'w': 140, 'x': 100, 'y': 100, 'z': 90,
                     'é': 92, 'á':100, 'ó':100, 'í':47, 'ú':100, 'ñ':105, '¿':90, '¡':52, ',':48, 'ã': 100}
        
        if effect == 'nightcore':
            img_path = 'resources/backgrounds/' + AutoChannel().playlist_infos[self.playlist]['img']
        elif effect == 'chipmunks':
            img_path = 'resources/backgrounds/chip.png'
        elif effect == 'male':
            img_path = 'resources/backgrounds/' + '_'.join(self.artists[0].lower().split()) + '.png'
            if '_'.join(self.artists[0].lower().split()) + '.png' not in os.listdir('resources/backgrounds'):
                print('Image does not exist, please create ' + '_'.join(self.artists[0].lower().split()) + '.png')
                input('Press enter when done')

        base = Image.open(img_path)
        fontsize = int(25e4 //  sum([char_size[char] if char in char_size else 100 for char in title]))
        font = ImageFont.truetype("resources\BebasNeue-Regular.ttf", fontsize)
        draw = ImageDraw.Draw(base)
        for x in [-5,0,5]:
            for y in [-5,0,5]:
                draw.text((140 + x,360 - (fontsize/2) + y), title, fill='black', font=font)
        draw.text((140, 360-(fontsize/2)), title, fill='white', font=font)
        draw = ImageDraw.Draw(base)
        base.save(self.create_file('_' + effect + '.png'))
        self.files['png_' + effect] = self.create_file('_' + effect + '.png')
    
    def create_video(self, effect):
        image = ImageClip(self.files['png_' + effect])
        if effect == 'nightcore':
            sound = AudioFileClip(self.files['wav_speed'])
        if effect == 'chipmunks':
            sound = AudioFileClip(self.files['wav_pitch_up'])
        if effect == 'male':
            sound = AudioFileClip(self.files['wav_pitch_down'])
        if sound.duration > 600 or sound.duration < 60:
            return 'audio too short or too long'
        image = image.set_duration(sound.duration)
        final_video = concatenate_videoclips([image], method="compose")
        final_video = final_video.set_audio(sound)
        final_video.write_videofile(self.create_file('_' + effect + '.mp4'), fps=20, preset='ultrafast',
                                    threads = 4, progress_bar=False, verbose=False)
        self.files['mp4_' + effect] = self.create_file('_' + effect + '.mp4')

    def pipeline(self, transformations = ['chipmunks', 'nightcore'], log=True):
        if log:
            print('\nStarting {}'.format(self.title_complete))
            print('1. Searching song on youtube : ', end='')
        self.step = 'search'
        self.find_song_on_youtube()
        if not self.files['url']:
            if log: print('Error')
            return 'song not found'
        if log: print('Done')
        
        if log: print('2. Downloading song : ', end='')
        self.step = 'download'
        self.download_song()
        if not self.files['m4a']:
            if log: print('Error')
            return 'download error'
        if log: print('Done')
        
        if log: print('3. Converting audio file to .wav : ', end='')
        self.step = 'convertion'
        self.convert()
        if not self.files['wav']:
            if log: print('Error')
            return 'convert error'
        if log: print('Done')
        
        if 'nightcore' in transformations:
            if log: print('4 (nightcore). Speeding up audio : ', end='')
            self.step = 'transformation'
            self.speed_up_song()
            if not self.files['wav_speed']:
                if log: print('Error')
                return 'speed up error'
            if log: print('Done')
        if 'chipmunks' in transformations:
            if log: print('4 (chipmunks). Pitching up audio : ', end='')
            self.step = 'transformation'
            self.pitch_up_song()
            if not self.files['wav_pitch_up']:
                if log: print('Error')
                return 'pitch up error'
            if log: print('Done')
        if 'male' in transformations:
            if log: print('4 (male). Pitching down audio : ', end='')
            self.step = 'transformation'
            self.pitch_down_song()
            if not self.files['wav_pitch_down']:
                if log: print('Error')
                return 'pitch down error'
            if log: print('Done')
            
        if 'nightcore' in transformations:
            if log: print('5 (nightcore). Creating background : ', end='')
            self.step = 'background'
            self.create_background(effect='nightcore')
            if not self.files['png_nightcore']:
                if log: print('Error')
                return 'background error (nightcore)'
            if log: print('Done')
        if 'chipmunks' in transformations:
            if log: print('5 (chipmunks). Creating background : ', end='')
            self.step = 'background'
            self.create_background(effect='chipmunks')
            if not self.files['png_chipmunks']:
                if log: print('Error')
                return 'background error (chipmunks)'
            if log: print('Done')
        if 'male' in transformations:
            if log: print('5 (male). Creating background : ', end='')
            self.step = 'background'
            self.create_background(effect='male')
            if not self.files['png_male']:
                if log: print('Error')
                return 'background error (male)'
            if log: print('Done')
        
        if 'nightcore' in transformations:
            if log: print('6 (nightcore). Generating video : ', end='')
            self.step = 'video'
            self.create_video(effect='nightcore')
            if not self.files['mp4_nightcore']:
                if log: print('Error')
                return 'video error (nightcore)'
            if log: print('Done')
        if 'chipmunks' in transformations:
            if log: print('6 (chipmunks). Generating video : ', end='')
            self.step = 'video'
            self.create_video(effect='chipmunks')
            if not self.files['mp4_chipmunks']:
                if log: print('Error')
                return 'video error (chipmunks)'
            if log: print('Done')
        if 'male' in transformations:
            if log: print('6 (male). Generating video : ', end='')
            self.step = 'video'
            self.create_video(effect='male')
            if not self.files['mp4_male']:
                if log: print('Error')
                return 'video error (male)'
            if log: print('Done')
        
        self.step = 'end'
        if log: print('Video created, ready to upload')
        return 'completed'

    def clean(self):
        for file in os.listdir('temp'):
            os.remove('temp/' + file)

class AutoChannel:
    def __init__(self):
        self.playlist_infos = {'Top Viral':{'uri':'spotify:user:spotifycharts:playlist:37i9dQZEVXbLiRSasKsNU9',
                                            'img':'nightcore_bpm.png'},
                            'Pop Rising':{'uri':'spotify:user:spotify:playlist:37i9dQZF1DWUa8ZRTfalHk',
                                               'img':'nightcore_pop.png'},
                            'Viva Latino':{'uri':'spotify:user:spotify:playlist:37i9dQZF1DX10zKzsJ2jva',
                                               'img':'nightcore_latino.png'},
                            'Rap Caviar':{'uri':'spotify:user:spotify:playlist:37i9dQZF1DX0XUsuxWHRQd',
                                               'img':'nightcore_rap.png'},
                            'Mint':{'uri':'spotify:user:spotify:playlist:37i9dQZF1DX4dyzvuaRJ0n',
                                               'img':'nightcore_mint.png'},
                            'Hot Country':{'uri':'spotify:user:spotify:playlist:37i9dQZF1DX1lVhptIYRda',
                                               'img':'nightcore_country.png'}}
        self.artist_bans = ['Willow Sage Hart', 'Calvin Harris', 'Dua Lipa', 'Various Artists', 'Kanye West',
                            'Jay Rock', 'Palaye Royale', 'Aimyon']
        self.keys = {'youtube_api_key':YOUTUBE_API_KEY,
                     'spotify_id':SPOTIFY_ID,
                     'spotify_secret':SPOTIFY_SECRET}
        self.sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=self.keys['spotify_id'],
                                                              client_secret=self.keys['spotify_secret']))
        
        self.clients = {'chipmunks':None, 'nightcore':None, 'male':None}
        self.new_songs = {'chipmunks':pd.DataFrame(), 'nightcore':pd.DataFrame(), 'male': pd.DataFrame()}

    def get_client(self, channel):
        self.clients[channel] = get_authenticated_service()

    def get_tracks(self, playlist):
        playlist_items = self.sp.user_playlist_tracks("spotify", playlist_id=self.playlist_infos[playlist]['uri'])['items']
        playlist_tracks = [(item['track']['name'], [artist['name'] for artist in item['track']['artists']],
                           item['track']['popularity']) for item in playlist_items]
        return pd.DataFrame(playlist_tracks, columns=['title', 'artists', 'popularity'])
    
    def get_new_songs(self, channel):
        my_songs = get_video_list(channel)
        new_songs = []
        
        for playlist in self.playlist_infos.keys():
            p_new_songs = self.get_tracks(playlist)
            p_new_songs = p_new_songs.loc[\
                         (p_new_songs['artists'].apply(lambda artists: not any(artist in self.artist_bans for artist in artists)))
                       & (p_new_songs['title'].apply(lambda title: not any(re.findall('[^([-]+', title)[0] in song for song in my_songs)))
                       ,:]
            if channel == 'male':
                def is_woman(artist, thresh=0.02):
                        r = requests.get("http://ws.audioscrobbler.com/2.0/?autocorrect=1&method=artist.getinfo&artist={}&api_key={}&format=json".format(artist.lower(), LASTFM_KEY)).json()
                        if 'artist' not in r:
                            return False
                        bio = r['artist']['bio']['content']
                        count_she_her = len(re.findall('(she|her) ', bio.lower()))
                        count_words = len(bio.split())
                        if count_words:
                            return count_she_her/count_words > thresh
                        else:
                            return False
                p_new_songs = p_new_songs.loc[p_new_songs['artists'].apply(lambda artists: len(artists)==1)]
                p_new_songs = p_new_songs.loc[p_new_songs['artists'].apply(lambda artists: is_woman(artists[0]))]
            
            print('{} : {} new songs'.format(playlist, p_new_songs.shape[0]))
            p_new_songs['playlist'] = playlist
            new_songs.append(p_new_songs)
            
        new_songs_df = pd.concat(new_songs, ignore_index=True).drop_duplicates('title', keep='last')
        new_songs_df['search_score'] = new_songs_df['artists'].apply(lambda artists:
            int(np.log(1 + np.max([get_result_number('intitle:{} "{}"'.format(channel, artist)) for artist in artists]))**2))
        new_songs_df['score'] = (new_songs_df['search_score'] + new_songs_df['popularity']) // 2
        new_songs_df.sort_values('score', ascending=False, inplace=True)
        self.new_songs[channel] = new_songs_df
            
    def create_and_upload_video(self, title, artists, playlist, channels=['nightcore', 'chipmunks']):
        videomaker = VideoMaker(title, artists, playlist)
        try:
            videomaker.pipeline(transformations=channels)
        except:
            pass
        if videomaker.step != 'end':
            return 'error'
        for channel in channels:
            upload(videomaker.files['mp4_'+ channel], videomaker.title_complete, channel, self.clients[channel])
            print('Video uploaded! ({})'.format(channel), end='\n\n')
        videomaker.clean()
        return 'uploaded'
            
    def upload_new_songs(self, channel, n=5, wait_factor=20):
        if not self.clients[channel]:
            self.get_client(channel)
        if self.new_songs[channel].shape[0] == 0:
            self.get_new_songs(channel)
        n = min(n, self.new_songs[channel].shape[0])
        
        i=0
        j=0
        while i<n and j<=self.new_songs[channel].shape[0]:
            title, artists, _, playlist, _, score = self.new_songs[channel].iloc[j]
            print('Song : {} / Artists : {} / Playlist : {} / Score : {}'.format(title, artists, playlist, score))
            status = self.create_and_upload_video(title, artists, playlist, channels=[channel])
            j+=1
            if status == 'uploaded':
                i+=1
                sleep(wait_factor*score)