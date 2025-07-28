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
import tempfile
import shutil
import atexit

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Create temporary downloads directory
temp_downloads_dir = Path(tempfile.mkdtemp(prefix="youtube_downloads_"))
logging.info(f"Created temporary downloads directory: {temp_downloads_dir}")

# Cleanup function to remove temp directory on exit
def cleanup_temp_dir():
    if temp_downloads_dir.exists():
        shutil.rmtree(temp_downloads_dir, ignore_errors=True)
        logging.info(f"Cleaned up temporary directory: {temp_downloads_dir}")

atexit.register(cleanup_temp_dir)

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
                'download_url': f'/download_file/{filename}',
                'file_path': d['filename']
            }
            logging.info(f"Download completed: {filename}")
            # Keep the progress for 10 minutes
            import threading
            def cleanup_progress():
                import time
                time.sleep(600)  # 10 minutes
                if self.video_id in download_progress:
                    del download_progress[self.video_id]
            threading.Thread(target=cleanup_progress, daemon=True).start()
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
                    
                    # Debug: Log all available formats
                    logging.debug(f"Total formats found: {len(info.get('formats', []))}")
                    
                    # Get video formats - include both combined and video-only streams
                    for f in info.get('formats', []):
                        # Video formats (including video-only streams)
                        if f.get('vcodec') != 'none':
                            quality = f.get('height')
                            if quality and quality >= 144:  # Include 144p and above
                                logging.debug(f"Found video format: {quality}p, codec: {f.get('vcodec')}, has_audio: {f.get('acodec') != 'none'}")
                                formats.append({
                                    'format_id': f.get('format_id'),
                                    'quality': f"{quality}p",
                                    'ext': f.get('ext'),
                                    'filesize': f.get('filesize'),
                                    'fps': f.get('fps'),
                                    'type': 'video',
                                    'has_audio': f.get('acodec') != 'none'
                                })
                        
                        # Audio-only formats
                        if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                            abr = f.get('abr')
                            if abr:
                                logging.debug(f"Found audio format: {int(abr)}kbps")
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
                    # Video format - combine video and audio for best quality
                    height = quality.replace('p', '')
                    format_selector = f'best[height<={height}]+bestaudio/best[height<={height}]/best'
                else:
                    format_selector = 'best'
                
                ydl_opts = {
                    'outtmpl': f'{temp_downloads_dir}/%(title)s.%(ext)s',
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
                    # Video format - combine video and audio for best quality
                    height = quality.replace('p', '')
                    format_selector = f'best[height<={height}]+bestaudio/best[height<={height}]/best'
                else:
                    format_selector = 'best'
                
                ydl_opts = {
                    'outtmpl': f'{temp_downloads_dir}/%(playlist_title)s/%(title)s.%(ext)s',
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
    """Serve downloaded files from temporary storage"""
    try:
        # Handle nested paths for playlists
        file_path = temp_downloads_dir / filename
        if file_path.exists() and file_path.is_file():
            logging.info(f"Serving temporary file: {filename}")
            return send_file(file_path, as_attachment=True)
        else:
            logging.error(f"Temporary file not found: {filename}")
            return jsonify({'error': 'File not found or expired'}), 404
    except Exception as e:
        logging.error(f"File download error: {str(e)}")
        return jsonify({'error': 'Download failed'}), 500

@app.route('/list_downloads')
def list_downloads():
    """List all available downloads from temporary storage"""
    try:
        downloads = []
        for file_path in temp_downloads_dir.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                relative_path = file_path.relative_to(temp_downloads_dir)
                downloads.append({
                    'filename': file_path.name,
                    'path': str(relative_path),
                    'size': file_path.stat().st_size,
                    'modified': file_path.stat().st_mtime
                })
        
        downloads.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify({'downloads': downloads})
    except Exception as e:
        logging.error(f"List downloads error: {str(e)}")
        return jsonify({'error': 'Failed to list downloads'}), 500

@app.route('/clear_downloads', methods=['POST'])
def clear_downloads():
    """Clear all temporary downloads"""
    try:
        # Remove all files from temp directory
        for file_path in temp_downloads_dir.rglob('*'):
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir() and file_path != temp_downloads_dir:
                shutil.rmtree(file_path, ignore_errors=True)
        
        # Clear progress tracking
        global download_progress
        download_progress = {}
        
        logging.info("Cleared all temporary downloads")
        return jsonify({'success': True, 'message': 'All downloads cleared'})
    except Exception as e:
        logging.error(f"Clear downloads error: {str(e)}")
        return jsonify({'error': 'Failed to clear downloads'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
