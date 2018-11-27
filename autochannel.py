import spotipy
import os
import re
import pafy
from spotipy.oauth2 import SpotifyClientCredentials
from youtube_functions import youtube_search, get_video_list, get_authenticated_service, upload
from pydub import AudioSegment
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from time import time, sleep
from PIL import Image, ImageFont, ImageDraw

class VideoMaker:
    def __init__(self, song_tuple, playlist):
        self.playlist = playlist
        self.title = song_tuple[0]
        self.artists = song_tuple[1].split(', ')
        self.title_complete = ' - '.join([self.title, [artist for artist in self.artists
                                                       if artist.lower() not in self.title.lower()]])
        self.title_simple = re.findall('^\w+(?: \w+)*', self.title)
        self.title_path = '_'.join(self.title_simple.split(' '))
        self.step = 'start'
        self.files = {'url':None, 'm4a':None, 'wav':None, 'wav_speed':None, 'wav_pitch':None,
                      'png_chipmunks':None, 'png_nightcore':None, 'mp4_chipmunks':None,
                      'mp4_nightcore':None}
    
    def create_file(self, extension, folder='temp/'):
        return folder + self.title_path + extension

    def find_song_on_youtube(self):
        q = ' '.join(re.findall('\w+', self.title_complete)) + ' lyrics'
        search = youtube_search(q)[1]
        video = search[0]
        video_title = video['snippet']['title'].lower()
        if re.findall('^\w+(?: \w+)*', self.title)[0] not in video_title\
        or any(word in video_title for word in ['reaction', 'trailer']):
            return 'song not found'
        self.files['url'] = "www.youtube.com/watch?v=" + video['id']['videoId']

    def download_song(self):
        video = pafy.new(self.files['url'])
        audiostreams = [stream for stream in video.audiostreams if stream.extension == 'm4a']
        self.files['m4a'] = audiostreams[0].download(filepath=create_file('temp/', '.m4a'), quiet=True)   

    def convert(self):
        sound = AudioSegment.from_file(self.files['m4a'])
        sound.export(self.create_file('temp/', '.wav'), format="wav")
        self.files['wav'] = self.create_file('temp/', '.wav')

    def pitch_up_song(self, pitch=8):
        os.chdir('rubberband')
        os.system('rubberband -t 1.0 -p {}.0 {} {}'.format(pitch, self.create_file('../temp/', '.wav'),
                  self.create_file('../temp/', '_pitch.wav')))
        os.chdir('..')
        self.files['wav_speed'] = self.create_file('temp/', '_pitch.wav')

    def speed_up_song(self, octaves=0.35):
        sound = AudioSegment.from_file(self.files['wav'])
        new_sample_rate = int(sound.frame_rate * (2.0 ** octaves))
        hipitch_sound = sound._spawn(sound.raw_data, overrides={'frame_rate': new_sample_rate})
        hipitch_sound = hipitch_sound.set_frame_rate(44100)
        hipitch_sound.export(create_file('temp/', '_speed.wav'), format="wav")
        self.files['wav_speed'] = create_file('temp/', '_speed.wav')

    def create_background(self, effect):
        title = self.title_simple.center(10, ' ')
        char_size = {' ': 40, '!': 52, '$': 100, '/': 100,  ':': 48, '?': 90, '-': 65, "'": 48, '0': 100,
                     '1': 100, '2': 100, '3': 100, '4': 100, '5': 100, '6': 100, '7': 100, '8': 100, '&':100,
                     '9': 100, 'a': 100, 'b': 100, 'c': 95, 'd': 100, 'e': 92, 'f': 88, 'g': 97, 'h': 105,
                     'i': 47, 'j': 65, 'k': 103, 'l': 85, 'm': 135, 'n': 105, 'o': 100, 'p': 95, 'q': 100,
                     'r': 100, 's': 90, 't': 92, 'u': 100, 'v': 95, 'w': 140, 'x': 100, 'y': 100, 'z': 90,
                     'é': 92, 'á':100, 'ó':100, 'í':47, 'ú':100, 'ñ':105, '¿':90, '¡':52, ',':48, 'ã': 100}
        
        if effect == 'nightcore':
            img_path = 'resources/' + AutoChannel().playlist_infos[self.playlist]['img']
        elif effect == 'chipmunks':
            img_path = 'resources/chip.png'

        base = Image.open(img_path)
        fontsize = 25e4 //  sum([char_size[char] if char in char_size else 100 for char in title])
        font = ImageFont.truetype("resources\BebasNeue-Regular.ttf", fontsize)
        draw = ImageDraw.Draw(base)
        for x in [-5,0,5]:
            for y in [-5,0,5]:
                draw.text((140 + x,360 - (fontsize/2) + y), title, fill='black', font=font)
        draw.text((140, 360-(fontsize/2)), new_title, fill='white', font=font)
        draw = ImageDraw.Draw(base)
        base.save(self.create_file('temp/', '.png'))
        self.files['png'] = self.create_file('temp/', '.png')
    
    def create_video(self, effect):
        image = ImageClip(self.files['png'])
        if effect == 'nightcore':
            sound = AudioFileClip(self.files['wav_speed'])
        if effect == 'chipmunks':
            sound = AudioFileClip(self.files['wav_pitch'])
        if sound.duration > 600 or sound.duration < 60:
            return 'audio too short or too long'
        image = image.set_duration(sound.duration)
        final_video = concatenate_videoclips([image], method="compose")
        final_video = final_video.set_audio(sound)
        final_video.write_videofile(self.create_file('temp/', '.mp4'), fps=20,
                                    preset='ultrafast', threads = 4, progress_bar=False)
        self.files['mp4'] = self.create_file('temp/', '.mp4')

    def pipeline(self, transformations = ['chipmunks', 'nightcore'], log=True):
        if log:
            print('\nStarting {}'.format(self.title_complete))
            print('1. Searching song on youtube : ', end='')
        self.step = 'search'
        self.find_songs_on_youtube()
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
            if log: print('5 (nightcore). Speeding up audio : ', end='')
            self.step = 'transformation'
            self.speed_up_song()
            if not self.files['wav_speed']:
                if log: print('Error')
                return 'speed up error'
            if log: print('Done')
        if 'chipmunks' in transformations:
            if log: print('5 (chipmunks). Pitching up audio : ', end='')
            self.step = 'transformation'
            self.pitch_up_song()
            if not self.files['wav_pitch']:
                if log: print('Error')
                return 'pitch up error'
            if log: print('Done')
        
        if 'nightcore' in transformations:
            if log: print('6 (nightcore). Creating background : ', end='')
            self.step = 'background'
            self.create_background(effect='nightcore')
            if not self.files['png_nightcore']:
                if log: print('Error')
                return 'background error (nightcore)'
            if log: print('Done')
        if 'chipmunks' in transformations:
            if log: print('6 (chipmunks). Creating background : ', end='')
            self.step = 'background'
            self.create_background(effect='chipmunks')
            if not self.files['png_chipmunks']:
                if log: print('Error')
                return 'background error (chipmunks)'
            if log: print('Done')
        
        if 'nightcore' in transformations:
            if log: print('7 (nightcore). Generating video : ', end='')
            self.step = 'video'
            self.create_video(effect='nightcore')
            if not self.files['mp4_nightcore']:
                if log: print('Error')
                return 'video error (nightcore)'
            if log: print('Done')
        if 'chipmunks' in transformations:
            if log: print('7 (chipmunks). Generating video : ', end='')
            self.step = 'video'
            self.create_video(effect='chipmunks')
            if not self.files['mp4_chipmunks']:
                if log: print('Error')
                return 'video error (chipmunks)'
            if log: print('Done')
            
        self.step = 'end'
        return 'completed'


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
                                               'img':'nightcore_country.png'},
                            'Rock This':{'uri':'spotify:user:spotify:playlist:37i9dQZF1DXcF6B6QPhFDv',
                                               'img':'nightcore_rock.png'},
                            'BPM':{'uri':'spotify:user:spotify:playlist:37i9dQZF1DX5wB72P2sVsT',
                                               'img':'nightcore_bpm.png'}}
        self.artist_bans = ['Willow Sage Hart', 'Calvin Harris', 'Dua Lipa', 'Various Artists', 'Kanye West',
                            'Jay Rock', 'Palaye Royale']
        self.keys = {'youtube_api_key':'AIzaSyBIjFukfphm1z-pTsMBwDmPmqZtW8Ia8hc',
                     'spotify_id':'72006f8475504777894fc7b149a68431',
                     'spotify_secret':'10faee29bac94e6a8f2a589f0977ccd3'}

        self.clients = {'chipmunks':None, 'nightcore':None}
        self.new_videos = {'chipmunks':{playlist: [] for playlist in self.playlist_infos.keys()},
                           'nightcore':{playlist: [] for playlist in self.playlist_infos.keys()}}

    def get_client(self, channel):
        self.clients[channel] = get_authenticated_service()

    def clean(self):
        for file in os.listdir('temp'):
            os.remove('temp/' + file)

    def get_tracks(self, playlist):
        client_credentials_manager = SpotifyClientCredentials(client_id=self.keys['spotify_id'],
                                                              client_secret=self.keys['spotify_secret'])
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        playlist_items = sp.user_playlist_tracks("spotify", playlist_id=self.playlist_infos[playlist]['uri'])['items']
        playlist_tracks = [(item['track']['name'], ', '.join([artist['name'] for artist in item['track']['artists']]))
                           for item in playlist_items]
        return playlist_tracks
    
    def get_new_songs(self, channel, playlists):
        my_songs = get_video_list(channel)
        for playlist in playlists:
            playlist_songs = self.get_tracks(playlist)
            playlist_songs = [song for song in playlist_songs
                              if (not any(artist in song[1] for artist in self.artist_bans))
                              and (not any(song[0][:5] in my_song and song[1][:5] in my_song
                                           for my_song in my_songs))]
            print('{} : {} new songs'.format(playlist, len(playlist_songs)))
            self.new_videos[channel][playlist] = playlist_songs