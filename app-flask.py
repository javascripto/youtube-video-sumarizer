from flask import Flask, render_template, request, jsonify
import yt_dlp
import os
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
from groq import Groq

# Carregar as variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # Carrega a chave da API do arquivo .env
client = Groq(api_key=GROQ_API_KEY)  # Inicializa o cliente Groq

def get_youtube_video_id(url):
    video_id = None

    if "youtube.com/watch" in url:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        video_id = query_params.get("v", [None])[0]
    elif "youtu.be" in url:
        path = urlparse(url).path
        video_id = path.split('/')[1] if '/' in path else path
    elif "youtube.com/embed" in url:
        path = urlparse(url).path
        video_id = path.split('/')[2] if len(path.split('/')) > 2 else None

    if video_id:
        video_id = video_id.split('?')[0].split('&')[0]

    return video_id

def download_caption(video_url):
    video_id = get_youtube_video_id(video_url)

    if not video_id:
        print("Não foi possível extrair o ID do vídeo.")
        return None

    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitlesformat': 'vtt',
        'subtitleslangs': ['pt', 'en'],
        'outtmpl': f'subtitles/{video_id}.%(ext)s'
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    subtitle_file_pt = f'subtitles/{video_id}.pt.vtt'
    if os.path.exists(subtitle_file_pt):
        with open(subtitle_file_pt, 'r', encoding='utf-8') as file:
            captions = file.read()
        return captions

    subtitle_file_en = f'subtitles/{video_id}.en.vtt'
    if os.path.exists(subtitle_file_en):
        with open(subtitle_file_en, 'r', encoding='utf-8') as file:
            captions = file.read()
        return captions

    print("Legendas não foram encontradas ou falha no download.")
    return None

def summarize_text(text):
    print("Usando o modelo llama-3.1-70b-versatile para resumir o texto.")

    chat_completion = client.chat.completions.create(
        model='llama-3.1-70b-versatile',
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant who speaks Portuguese "
                           "and summarizes texts. Very important: do not "
                           "summarize the text in the same language as the "
                           "original text but in Portuguese."
            },
            {
                "role": "user",
                "content": "Summarize the following caption text from a "
                           "YouTube video so that I don't have to watch "
                           "the entire video to know what it's about. "
                           "Get the main idea and avoid wordiness. "
                           "Show the summary in a structured way by "
                           "breaking up lines with html tags like h3, p, ul, ol, li"
                           f":\n\n{text}"
            }
        ]
    )
    return chat_completion.choices[0].message.content

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        video_urls = request.form.get('urls').split()
        summaries = []

        for url in video_urls:
            captions = download_caption(url)
            if captions:
                summary = summarize_text(captions)
                summaries.append({'url': url, 'summary': summary})
            else:
                summaries.append({'url': url, 'summary': 'Legendas não encontradas ou falha no download'})

        return jsonify(summaries)

    return render_template('index.html')

if __name__ == '__main__':
    if not os.path.exists('subtitles'):
        os.makedirs('subtitles')
    app.run(debug=True)