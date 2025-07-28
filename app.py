import os
import logging
import json
import re
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
import yt_dlp
from urllib.parse import urlparse, parse_qs
import threading
import time
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Create downloads directory
downloads_dir = Path("downloads")
downloads_dir.mkdir(exist_ok=True)

# Global variable to store download progress
download_progress = {}

class ProgressHook:
    def __init__(self, video_id):
        self.video_id = video_id
    
    def __call__(self, d):
        if d['status'] == 'downloading':
            try:
                percent = d.get('_percent_str', '0%').replace('%', '')
                speed = d.get('_speed_str', 'N/A')
                eta = d.get('_eta_str', 'N/A')
                
                download_progress[self.video_id] = {
                    'status': 'downloading',
                    'percent': float(percent) if percent != 'N/A' else 0,
                    'speed': speed,
                    'eta': eta
                }
            except (ValueError, TypeError):
                download_progress[self.video_id] = {
                    'status': 'downloading',
                    'percent': 0,
                    'speed': 'N/A',
                    'eta': 'N/A'
                }
        elif d['status'] == 'finished':
            filename = Path(d['filename']).name
            download_progress[self.video_id] = {
                'status': 'finished',
                'percent': 100,
                'filename': filename,
                'download_url': f'/download_file/{filename}'
            }
        elif d['status'] == 'error':
            download_progress[self.video_id] = {
                'status': 'error',
                'error': str(d.get('error', 'Unknown error'))
            }

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if video_id_match:
        return video_id_match.group(1)
    return None

def is_valid_youtube_url(url):
    """Validate if URL is a valid YouTube URL"""
    youtube_domains = ['youtube.com', 'youtu.be', 'www.youtube.com', 'm.youtube.com']
    try:
        parsed_url = urlparse(url)
        return parsed_url.netloc.lower() in youtube_domains
    except:
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_video_info', methods=['POST'])
def get_video_info():
    try:
        url = request.json.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        if not is_valid_youtube_url(url):
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                
                if info.get('_type') == 'playlist':
                    # Handle playlist
                    videos = []
                    for entry in info.get('entries', [])[:20]:  # Limit to first 20 videos
                        if entry:
                            video_info = {
                                'id': entry.get('id'),
                                'title': entry.get('title'),
                                'thumbnail': entry.get('thumbnail'),
                                'duration': entry.get('duration'),
                                'uploader': entry.get('uploader'),
                                'view_count': entry.get('view_count'),
                                'url': entry.get('webpage_url')
                            }
                            videos.append(video_info)
                    
                    return jsonify({
                        'type': 'playlist',
                        'title': info.get('title'),
                        'uploader': info.get('uploader'),
                        'video_count': len(videos),
                        'videos': videos
                    })
                else:
                    # Handle single video
                    formats = []
                    audio_formats = []
                    
                    # Get video formats
                    for f in info.get('formats', []):
                        if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                            quality = f.get('height')
                            if quality:
                                formats.append({
                                    'format_id': f.get('format_id'),
                                    'quality': f"{quality}p",
                                    'ext': f.get('ext'),
                                    'filesize': f.get('filesize'),
                                    'fps': f.get('fps'),
                                    'type': 'video'
                                })
                        elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                            # Audio-only formats
                            abr = f.get('abr')
                            if abr:
                                audio_formats.append({
                                    'format_id': f.get('format_id'),
                                    'quality': f"{int(abr)}kbps",
                                    'ext': f.get('ext'),
                                    'filesize': f.get('filesize'),
                                    'type': 'audio'
                                })
                    
                    # Remove duplicates and sort video formats by quality
                    seen = set()
                    unique_formats = []
                    for f in formats:
                        quality_key = f['quality']
                        if quality_key not in seen:
                            seen.add(quality_key)
                            unique_formats.append(f)
                    
                    unique_formats.sort(key=lambda x: int(x['quality'].replace('p', '')), reverse=True)
                    
                    # Add audio formats
                    audio_seen = set()
                    unique_audio = []
                    for f in audio_formats:
                        quality_key = f['quality']
                        if quality_key not in seen and quality_key not in audio_seen:
                            audio_seen.add(quality_key)
                            unique_audio.append(f)
                    
                    unique_audio.sort(key=lambda x: int(x['quality'].replace('kbps', '')), reverse=True)
                    
                    # Combine all formats
                    all_formats = unique_formats + unique_audio
                    
                    video_info = {
                        'type': 'video',
                        'id': info.get('id'),
                        'title': info.get('title'),
                        'thumbnail': info.get('thumbnail'),
                        'duration': info.get('duration'),
                        'uploader': info.get('uploader'),
                        'view_count': info.get('view_count'),
                        'description': info.get('description', '')[:500] + '...' if info.get('description') and len(info.get('description')) > 500 else info.get('description', ''),
                        'formats': all_formats[:20]  # Show more format options
                    }
                    
                    return jsonify(video_info)
                    
            except Exception as e:
                logging.error(f"Error extracting video info: {str(e)}")
                return jsonify({'error': f'Failed to extract video information: {str(e)}'}), 400
                
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/download_video', methods=['POST'])
def download_video():
    try:
        data = request.json
        url = data.get('url', '').strip()
        quality = data.get('quality', 'best')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        if not is_valid_youtube_url(url):
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({'error': 'Could not extract video ID'}), 400
        
        # Initialize progress tracking
        download_progress[video_id] = {'status': 'starting', 'percent': 0}
        
        def download_thread():
            try:
                # Determine format based on quality selection
                if quality == 'best':
                    format_selector = 'best'
                elif 'kbps' in quality:
                    # Audio only format
                    format_selector = 'bestaudio/best'
                    if quality != 'best':
                        # Try to get specific audio quality
                        abr = quality.replace('kbps', '')
                        format_selector = f'bestaudio[abr<={abr}]/bestaudio/best'
                elif 'p' in quality:
                    # Video format
                    height = quality.replace('p', '')
                    format_selector = f'best[height<={height}]/best'
                else:
                    format_selector = 'best'
                
                ydl_opts = {
                    'outtmpl': f'downloads/%(title)s.%(ext)s',
                    'progress_hooks': [ProgressHook(video_id)],
                    'format': format_selector,
                }
                
                # If audio only, convert to mp3
                if 'kbps' in quality:
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': quality.replace('kbps', '') if quality != 'best' else '192',
                    }]
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                    
            except Exception as e:
                logging.error(f"Download error: {str(e)}")
                download_progress[video_id] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Start download in background thread
        thread = threading.Thread(target=download_thread)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'message': 'Download started'
        })
        
    except Exception as e:
        logging.error(f"Download initialization error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_playlist', methods=['POST'])
def download_playlist():
    try:
        data = request.json
        url = data.get('url', '').strip()
        quality = data.get('quality', 'best')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        if not is_valid_youtube_url(url):
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        playlist_id = f"playlist_{int(time.time())}"
        download_progress[playlist_id] = {'status': 'starting', 'percent': 0}
        
        def download_playlist_thread():
            try:
                # Determine format based on quality selection
                if quality == 'best':
                    format_selector = 'best'
                elif 'kbps' in quality:
                    # Audio only format
                    format_selector = 'bestaudio/best'
                    if quality != 'best':
                        abr = quality.replace('kbps', '')
                        format_selector = f'bestaudio[abr<={abr}]/bestaudio/best'
                elif 'p' in quality:
                    # Video format
                    height = quality.replace('p', '')
                    format_selector = f'best[height<={height}]/best'
                else:
                    format_selector = 'best'
                
                ydl_opts = {
                    'outtmpl': f'downloads/%(playlist_title)s/%(title)s.%(ext)s',
                    'progress_hooks': [ProgressHook(playlist_id)],
                    'format': format_selector,
                }
                
                # If audio only, convert to mp3
                if 'kbps' in quality:
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': quality.replace('kbps', '') if quality != 'best' else '192',
                    }]
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                    
            except Exception as e:
                logging.error(f"Playlist download error: {str(e)}")
                download_progress[playlist_id] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Start download in background thread
        thread = threading.Thread(target=download_playlist_thread)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'playlist_id': playlist_id,
            'message': 'Playlist download started'
        })
        
    except Exception as e:
        logging.error(f"Playlist download initialization error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_progress/<video_id>')
def get_download_progress(video_id):
    progress = download_progress.get(video_id, {'status': 'not_found'})
    return jsonify(progress)

@app.route('/download_file/<path:filename>')
def download_file(filename):
    """Serve downloaded files"""
    try:
        file_path = downloads_dir / filename
        if file_path.exists() and file_path.is_file():
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logging.error(f"File download error: {str(e)}")
        return jsonify({'error': 'Download failed'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
