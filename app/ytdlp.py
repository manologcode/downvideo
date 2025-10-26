import yt_dlp
import re
import os
import unicodedata

folder_sub="/resources/subtitles/"
folder_video="/resources/videos/"
folder_audio="/resources/audios/"

def get_cookie_opts():
    """Returns cookie configuration if cookies.txt exists and has content, otherwise returns empty dict"""
    if os.path.exists('cookies.txt'):
        # Check if the file has content (not empty)
        if os.path.getsize('cookies.txt') > 0:
            print("Using cookies.txt for authentication...")
            return {'cookiefile': 'cookies.txt'}
        else:
            print("Warning: cookies.txt is empty. Continuing without cookies. Some private/restricted videos may not be accessible.")
            return {}
    else:
        print("Warning: cookies.txt not found. Continuing without cookies. Some private/restricted videos may not be accessible.")
        return {}

def get_available_subtitles(video_url):
    ydl_opts = {
        'http_headers': {
            'Accept-Encoding': 'identity;q=1, *;q=0',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
        'skip_download': True,
        'writesubtitles': True,
        'listsubtitles': True,
    }
    
    # Add cookies if available
    ydl_opts.update(get_cookie_opts())

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=False)
        subtitles = info_dict.get('subtitles', {})
        automatic_captions = info_dict.get('automatic_captions', {})
        return subtitles, automatic_captions

def normalize_name(text):
    nfkd_form = unicodedata.normalize('NFKD', text)
    only_ascii = nfkd_form.encode('ASCII', 'ignore').decode('ASCII')
    normalized = re.sub(r'[^a-zA-Z0-9\s]', '', only_ascii)
    final_filename = normalized.replace(' ', '_')
    final_filename = final_filename.lower()
    return final_filename

def descargar_subtitulos(video_url, lang='es', automatic_subs=False, task_id=None):
    # Usar task_id para crear nombre temporal único
    temp_filename = f"temp_sub_{task_id}" if task_id else "text_origin"
    
    ydl_opts = {
        'http_headers': {
            'Accept-Encoding': 'identity;q=1, *;q=0',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
        'writesubtitles': True,
        'subtitleslangs': [lang],
        'skip_download': True,
        'outtmpl': folder_sub + temp_filename,
    }
    
    # Add cookies if available
    ydl_opts.update(get_cookie_opts())
    
    if automatic_subs:
        ydl_opts['writeautomaticsub'] = True

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
        subtitle_filename = normalize_name(info['title']) + f'.{lang}.vtt'
        os.rename(folder_sub + f'{temp_filename}.{lang}.vtt',folder_sub +  subtitle_filename)
        response={'title': info['title'],
                  'file_name': normalize_name(info['title']),
                  'name_vtt':subtitle_filename
                   }
        return response
    except Exception as e:
        print(f"Error al descargar subtítulos: {e}")
        return None

def extraer_texto_vtt(srt_filename):
    path_file = os.path.join(folder_sub, srt_filename)
    print("convirtiendo fichero"+path_file)
    if os.path.isfile(path_file):
        with open(path_file, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        text_lines = ""
        last_item = ""
        for line in lines:

            line = re.sub(r'\[.*?\]', '', line)

            if '-->' in line or line == last_item or '<c>' in line or line.strip() == '' or line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
                continue
            last_item = line
            last_line = line.strip() 
            if last_line.endswith('.'):
                last_line += "\n"
            else:
                last_line += " "
            last_line
            text_lines += last_line

        text_name_file = path_file[:-4] + ".txt"

        with open(text_name_file, 'w') as archivo:
            archivo.write(text_lines)
        print(f"Archivo guardado como -> {text_name_file}")
        return text_lines
    else:
        print(f"El archivo {path_file} no existe.")
        return None    

def download_sub(video_url, lang='es', task_id=None):
    response = None
    subtitles, auto_subtitles = get_available_subtitles(video_url)
    name_sub = list(subtitles.keys())
    num_sub = len(name_sub)
    if num_sub > 0:
        if num_sub == 1:
            lang = name_sub[0]
        print(f"Descargando subtítulos normales en el idioma:{lang}")
        vtt_response = descargar_subtitulos(video_url, lang, automatic_subs=False, task_id=task_id)
    else:
        if lang not in auto_subtitles:
            l_orig = [lang for lang in auto_subtitles if '-orig' in lang][0]
            lang = l_orig if l_orig  else 'en'
        print(f"subtitulos automaticos en {lang}.")
        vtt_response = descargar_subtitulos(video_url, lang, automatic_subs=True, task_id=task_id)
    if vtt_response:
        response ={ 
          "title": vtt_response['title'],
          "file_name": vtt_response['file_name'],
          "lang": lang,
          "text": extraer_texto_vtt(vtt_response['name_vtt'])
      }

    return  response

def obtener_titulo_video_youtube(video_url):
    # Opciones de yt-dlp
    ydl_opts = {
        'http_headers': {
            'Accept-Encoding': 'identity;q=1, *;q=0',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
        'quiet': True,
        'skip_download': True,
        'force_generic_extractor': True,
    }
    
    # Add cookies if available
    ydl_opts.update(get_cookie_opts())

    # Crear instancia de yt-dlp
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Extraer información del video
        info_dict = ydl.extract_info(video_url, download=False)
        # Obtener el título del video
        titulo = info_dict.get('title', 'No se encontró el título')
        return titulo

def download_video(url, task_id=None):
    if not os.path.exists(folder_video):
        os.makedirs(folder_video)
    
    # Usar task_id para crear nombre temporal único
    temp_filename = f"temp_video_{task_id}" if task_id else "nuevo_video"
    
    ydl_opts = {
        'http_headers': {
            'Accept-Encoding': 'identity;q=1, *;q=0',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4', 
        'outtmpl': folder_video + f"{temp_filename}.mp4",
        'merge_output_format': 'mp4',
    }
    
    # Add cookies if available
    ydl_opts.update(get_cookie_opts())

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        info = ydl.extract_info(url, download=True)
        video_filename = normalize_name(info['title']) + '.mp4'
        os.rename(folder_video + f'{temp_filename}.mp4',folder_video +  video_filename)


    response={'title': info['title'],
            'file_name': video_filename,
            }
    return response


def download_audio(url, task_id=None):
    if not os.path.exists(folder_audio):
        os.makedirs(folder_audio)

    # Usar task_id para crear nombre temporal único
    temp_filename = f"temp_audio_{task_id}" if task_id else "nuevo_audio"

    ydl_opts = {
        'http_headers': {
            'Accept-Encoding': 'identity;q=1, *;q=0',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
        'format': 'bestaudio/best',  # Selecciona la mejor calidad de audio disponible
        'outtmpl': folder_audio + temp_filename,
        'postprocessors': [{  # Utiliza postprocesadores para convertir el audio a MP3
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'ffmpeg_location': '/usr/bin/ffmpeg',  # Opcional: especifica la ubicación de ffmpeg si no está en el PATH
    }
    
    # Add cookies if available
    ydl_opts.update(get_cookie_opts())

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        info = ydl.extract_info(url, download=True)
        audio_filename = normalize_name(info['title']) + '.mp3'
        os.rename(folder_audio + f'{temp_filename}.mp3',folder_audio +  audio_filename)

    response={'title': info['title'],
            'file_name': audio_filename,
            }
    return response

if __name__ == '__main__':
    video_url = 'https://www.youtube.com/watch?v=HqREUMMXvg8'
    download_video(video_url)