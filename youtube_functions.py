import requests
import os
import httplib2
import random
import time
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build

DEVELOPER_KEY = "AIzaSyBIjFukfphm1z-pTsMBwDmPmqZtW8Ia8hc"
youtube = build("youtube", "v3", developerKey=DEVELOPER_KEY)

def youtube_search(q):

  search_response = youtube.search().list(
    q=q,
    type="video",
    pageToken=None,
    order = 'relevance',
    part="id,snippet",
    maxResults=50,
    location=None,
    locationRadius=None
  ).execute()

  videos = []

  for search_result in search_response.get("items", []):
    if search_result["id"]["kind"] == "youtube#video":
      videos.append(search_result)
  try:
      nexttok = search_response["nextPageToken"]
      return(nexttok, videos)
  except Exception as e:
      nexttok = "last_page"
      return(nexttok, videos)

def get_video_list(channel):
    if channel == 'chipmunks':
        playlist_id = 'UUeZz51d6hoLYapE8omsuK_Q'
    elif channel == 'nightcore':
        playlist_id = 'UUhvVVC6xPA0MWzkt78nKm6Q'
    elif channel == 'male':
        playlist_id = 'UUrxcDHzoHC3O7aeNS18YrXQ'
    results = []
    link = "https://www.googleapis.com/youtube/v3/playlistItems"
    req = requests.get("{}?playlistId={}&key={}&part=snippet&maxResults=50".format(link, playlist_id, DEVELOPER_KEY))
    results.extend([item['snippet']['title'] for item in req.json()['items']])
    while 'nextPageToken' in req.json():
        req = requests.get("{}?playlistId={}&key={}&part=snippet&maxResults=50&pageToken={}".format(link, playlist_id, DEVELOPER_KEY, req.json()['nextPageToken']))
        results.extend([item['snippet']['title'] for item in req.json()['items']])
    return results

def get_result_number(q):
    return youtube.search().list(
            q=q, part='snippet'
           ).execute()['pageInfo']['totalResults']
    
# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret.
CLIENT_SECRETS_FILE = 'client_secret.txt'

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

def get_authenticated_service():
  flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
  credentials = flow.run_local_server()
  return build(API_SERVICE_NAME, API_VERSION, credentials = credentials)


# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(request, resource, method):
  response = None
  error = None
  retry = 0
  while response is None:
    status, response = request.next_chunk()
    if response is not None:
      if method == 'insert' and 'id' in response:
        pass
      elif method != 'insert' or 'id' not in response:
        print(response)
      else:
        exit("The upload failed with an unexpected response: %s" % response)

    if error is not None:
      print(error)
      retry += 1
      if retry > MAX_RETRIES:
        exit("No longer attempting to retry.")

      max_sleep = 2 ** retry
      sleep_seconds = random.random() * max_sleep
      print("Sleeping %f seconds and then retrying..." % sleep_seconds)
      time.sleep(sleep_seconds)
      
def print_response(response):
  print(response)

# Build a resource based on a list of properties given as key-value pairs.
# Leave properties with empty values out of the inserted resource.
def build_resource(properties):
  resource = {}
  for p in properties:
    prop_array = p.split('.')
    ref = resource
    for pa in range(0, len(prop_array)):
      is_array = False
      key = prop_array[pa]
      if key[-2:] == '[]':
        key = key[0:len(key)-2:]
        is_array = True

      if pa == (len(prop_array) - 1):
        if properties[p]:
          if is_array:
            ref[key] = properties[p].split(',')
          else:
            ref[key] = properties[p]
      elif key not in ref:
        ref[key] = {}
        ref = ref[key]
      else:
        ref = ref[key]
  return resource

# Remove keyword arguments that are not set
def remove_empty_kwargs(**kwargs):
  good_kwargs = {}
  if kwargs is not None:
    for key, value in kwargs.items():
      if value:
        good_kwargs[key] = value
  return good_kwargs

def videos_insert(client, properties, media_file, **kwargs):
  resource = build_resource(properties)
  kwargs = remove_empty_kwargs(**kwargs)
  request = client.videos().insert(
    body=resource,
    media_body=MediaFileUpload(media_file, chunksize=-1,
                               resumable=True),
    **kwargs
  )

  return resumable_upload(request, 'video', 'insert')


def upload(media_file, title, channel, client):
  os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
  
  if channel == 'chipmunks':
      tags = 'chipmunks, chipettes, alvin, alvin and the chipmunks, remix, {}'.format(title.replace('-', ','))
  elif channel == 'nightcore':
      tags = 'nightcore, music, anime, remix, {}'.format(title.replace('-', ','))
  elif channel == 'male':
      tags = 'male, male version, remix, pitch, {}'.format(title.replace('-', ','))
      channel = 'male version'
      
  videos_insert(client, 
    {'snippet.categoryId': '10',
     'snippet.defaultLanguage': '',
     'snippet.description': '{} {} - Post your suggestions in the comments!\nIf you want to support me : https://www.tipeeestream.com/nightcore-universe/donation, thanks a lot :)'.format(channel.title(), title),
     'snippet.tags[]': tags,
     'snippet.title': '({}) {}'.format(channel.upper(), title),
     'status.embeddable': '',
     'status.license': '',
     'status.privacyStatus': 'public',
     'status.publicStatsViewable': ''},
    media_file,
    part='snippet,status')