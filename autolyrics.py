import pytesseract
from PIL import Image
import requests
import bs4
import re
from fuzzywuzzy import fuzz

pytesseract.pytesseract.tesseract_cmd = r"D:\Python\Youtube\resources\tesseract\tesseract.exe"

class OCRLyrics:
    def __init__(self, title, artists):
        self.title = title
        self.artists = artists
        self.lyrics_website = []

    def preprocess_lyrics(self, lyrics):
        lyrics_clean = [line.lower() for line in re.split('(\r|\n)+', lyrics) if re.search('\w', line)]
        return lyrics_clean

    def ocr(self, img_path = 'temp/test.png'):
        img = Image.open(img_path)
        lyrics_ocr = pytesseract.image_to_string(img)
        lyrics_ocr_clean = self.preprocess_lyrics(lyrics_ocr)
        return lyrics_ocr_clean
    
    def get_lyrics_online(self):
        website =  'https://search.azlyrics.com'
        r = requests.get(website + '/search.php?q={}+{}'.format('+'.join(self.title.lower().split()),
                                                                '+'.join(self.artists[0].lower().split())))
        soup = bs4.BeautifulSoup(r.content, 'lxml')
        lyrics_page = soup.findAll("div", {"class": "panel"})[0].findAll("a")[0].get("href")
        
        r = requests.get(lyrics_page)
        soup = bs4.BeautifulSoup(r.content, 'lxml')
        
        lyrics = soup.findAll('div')[21].text
        lyrics_clean = self.preprocess_lyrics(lyrics)
        self.lyrics_website = lyrics_clean
    
    def match_lyrics(self, lyrics_ocr):
        max_score = 0
        ocr_length = len(lyrics_ocr)
        best = []
        for i in range(len(self.lyrics_website)-ocr_length):
            test_lyrics = self.lyrics_website[i:i+ocr_length]
            score = sum([fuzz.ratio(ocr, website) for ocr, website in zip(lyrics_ocr, test_lyrics)])//ocr_length
            if score > max_score:
                max_score = score
                best = test_lyrics
        return best, max_score
    
    def ocr_match(self, img_path):
        lyrics_ocr = self.ocr(img_path)
        if not self.lyrics_website:
            self.get_lyrics_online()
        lyrics_match, score = self.match_lyrics(lyrics_ocr)
        return lyrics_match, score
            
        