import streamlit as st
import yt_dlp
import os
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
from groq import Groq

# Carregar as variáveis do arquivo .env
load_dotenv()

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
        st.error("Não foi possível extrair o ID do vídeo.")
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

    st.error("Legendas não foram encontradas ou falha no download.")
    return None

def summarize_text(text):
    st.info("Usando o modelo llama-3.1-70b-versatile para resumir o texto.")

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

def main():
    st.title("YouTube Video Summarizer with Groq")

    video_url = st.text_input("Enter YouTube Video URL")

    if st.button("Generate Summary"):
        if video_url:
            captions = download_caption(video_url)
            if captions:
                summary = summarize_text(captions)
                st.markdown(summary, unsafe_allow_html=True)
            else:
                st.error("Failed to download captions or no captions available.")
        else:
            st.error("Please enter a valid YouTube URL.")

if __name__ == '__main__':
    if not os.path.exists('subtitles'):
        os.makedirs('subtitles')
    main()