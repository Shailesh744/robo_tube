# YouTube Video Downloader

## Overview

This is a Flask-based web application for downloading YouTube videos and playlists. The application provides a user-friendly interface where users can input YouTube URLs and download content in various formats and qualities. It uses yt-dlp (youtube-dl fork) for video extraction and downloading capabilities.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Technology**: HTML5, CSS3, JavaScript (vanilla)
- **UI Framework**: Bootstrap 5.3.0 for responsive design
- **Icons**: Font Awesome 6.4.0 for iconography
- **Architecture Pattern**: Single Page Application (SPA) with dynamic content updates
- **Styling**: Custom CSS with CSS variables for theming and gradients

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Architecture Pattern**: Simple monolithic structure
- **Request Handling**: RESTful API endpoints for video info fetching and downloading
- **Session Management**: Flask's built-in session handling with secret key
- **File Handling**: Local file system storage in `downloads/` directory

### Core Components
- **Main Application**: `app.py` - Contains all Flask routes and business logic
- **Entry Point**: `main.py` - Simple application runner
- **Progress Tracking**: In-memory progress tracking using global variables
- **Download Management**: Threading support for concurrent downloads

## Key Components

### Video Download Engine
- **Library**: yt-dlp for YouTube video extraction
- **Progress Tracking**: Custom ProgressHook class for real-time download updates
- **Format Support**: Multiple video qualities and formats
- **Error Handling**: Comprehensive error catching and user feedback

### User Interface Components
- **URL Input Form**: Bootstrap-styled form for YouTube URL submission
- **Video Information Display**: Dynamic content showing video metadata
- **Progress Indicators**: Real-time download progress with speed and ETA
- **Responsive Design**: Mobile-first approach with Bootstrap grid system

### File Management
- **Download Directory**: Automatic creation of `downloads/` folder
- **File Serving**: Flask's send_file for download delivery
- **Path Handling**: Python's pathlib for cross-platform compatibility

## Data Flow

1. **URL Submission**: User submits YouTube URL through web form
2. **Video Info Extraction**: yt-dlp extracts video metadata without downloading
3. **Format Selection**: User chooses preferred video quality/format
4. **Download Initiation**: Background thread starts download process
5. **Progress Updates**: Real-time progress updates via AJAX polling
6. **File Delivery**: Completed files served through Flask route

## External Dependencies

### Python Packages
- **Flask**: Web framework for HTTP handling and templating
- **yt-dlp**: YouTube video downloading and metadata extraction
- **pathlib**: Modern path handling (Python standard library)
- **threading**: Concurrent download processing (Python standard library)
- **logging**: Application logging and debugging (Python standard library)

### Frontend Dependencies
- **Bootstrap 5.3.0**: CSS framework for responsive UI components
- **Font Awesome 6.4.0**: Icon library for enhanced visual elements
- **CDN Delivery**: External CSS/JS libraries loaded from CDNs

### System Dependencies
- **File System**: Local storage for downloaded video files
- **Network Access**: Required for YouTube API access and video downloading

## Deployment Strategy

### Development Environment
- **Debug Mode**: Flask debug mode enabled for development
- **Host Configuration**: Binds to 0.0.0.0:5000 for external access
- **Environment Variables**: SESSION_SECRET for production security

### File Structure Requirements
- **Static Assets**: CSS and JavaScript files in `static/` directory
- **Templates**: HTML templates in `templates/` directory
- **Downloads**: Automatic creation of `downloads/` directory for video storage

### Security Considerations
- **Secret Key**: Configurable session secret via environment variable
- **URL Validation**: Input validation for YouTube URLs
- **File Access**: Controlled file serving through Flask routes

### Scalability Limitations
- **In-Memory Storage**: Progress tracking uses global variables (not suitable for multiple instances)
- **Local File Storage**: Downloads stored locally (not suitable for distributed deployment)
- **Threading Model**: Simple threading approach (may need queue system for high traffic)

## Recent Changes (July 2025)

### Enhanced Download Capabilities
- **Multiple Quality Options**: Added support for all available video qualities (4K, 1440p, 1080p, 720p, 480p, 360p, 240p)
- **Audio-Only Downloads**: Implemented MP3 extraction with multiple bitrate options (320kbps, 256kbps, 192kbps, 128kbps, 96kbps)
- **Smart Format Detection**: Separate video and audio format groups in UI for better user experience
- **FFmpeg Integration**: Added FFmpeg for high-quality audio conversion to MP3

### Improved User Interface
- **Grouped Quality Selection**: Video and audio options are now properly categorized in dropdown menus
- **File Size Display**: Shows estimated file sizes for each quality option when available
- **Download Links**: Automatic download links appear when files are ready
- **Real-time Progress**: Enhanced progress tracking with speed and ETA information

### Technical Improvements
- **Better Format Selection**: Enhanced yt-dlp format selectors for optimal quality matching
- **Error Handling**: Improved error messages and download state management
- **File Serving**: Added secure file download routes for completed downloads

## Technical Notes

The application follows a simple monolithic architecture suitable for small to medium-scale deployments. The codebase is now complete with full ProgressHook implementation and comprehensive download functionality.

Key architectural decisions prioritize simplicity and ease of deployment over scalability, making it ideal for personal use or small-scale deployments. The use of yt-dlp provides robust YouTube integration with professional-grade format selection, while Bootstrap ensures a professional, responsive user interface that matches commercial video downloaders.