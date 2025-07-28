class YouTubeDownloader {
    constructor() {
        this.currentVideoId = null;
        this.currentPlaylistId = null;
        this.progressInterval = null;
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        const urlForm = document.getElementById('urlForm');
        const downloadVideoBtn = document.getElementById('downloadVideoBtn');
        const downloadPlaylistBtn = document.getElementById('downloadPlaylistBtn');
        const clearDownloadsBtn = document.getElementById('clear-downloads');

        urlForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.fetchVideoInfo();
        });

        downloadVideoBtn.addEventListener('click', () => {
            this.downloadVideo();
        });

        downloadPlaylistBtn.addEventListener('click', () => {
            this.downloadPlaylist();
        });
        
        if (clearDownloadsBtn) {
            clearDownloadsBtn.addEventListener('click', () => {
                this.clearDownloads();
            });
        }
        
        // Auto-clear downloads on page load (simulating refresh behavior)
        this.clearDownloadsOnLoad();
    }

    showLoading() {
        this.hideAll();
        document.getElementById('loadingState').classList.remove('d-none');
    }

    hideLoading() {
        document.getElementById('loadingState').classList.add('d-none');
    }

    showError(message) {
        this.hideAll();
        const errorDisplay = document.getElementById('errorDisplay');
        const errorMessage = document.getElementById('errorMessage');
        errorMessage.textContent = message;
        errorDisplay.classList.remove('d-none');
        errorDisplay.classList.add('fade-in');
    }

    hideAll() {
        document.getElementById('loadingState').classList.add('d-none');
        document.getElementById('errorDisplay').classList.add('d-none');
        document.getElementById('videoInfo').classList.add('d-none');
        document.getElementById('singleVideoInfo').classList.add('d-none');
        document.getElementById('playlistInfo').classList.add('d-none');
        document.getElementById('downloadProgress').classList.add('d-none');
    }

    formatDuration(seconds) {
        if (!seconds) return 'N/A';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainingSeconds = seconds % 60;
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
        }
    }

    formatNumber(num) {
        if (!num) return '0';
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    formatFileSize(bytes) {
        if (!bytes) return 'Unknown';
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }

    async fetchVideoInfo() {
        const url = document.getElementById('urlInput').value.trim();
        
        if (!url) {
            this.showError('Please enter a YouTube URL');
            return;
        }

        this.showLoading();

        try {
            const response = await fetch('/get_video_info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to fetch video information');
            }

            this.hideLoading();
            this.displayVideoInfo(data);

        } catch (error) {
            console.error('Error fetching video info:', error);
            this.showError(error.message || 'Failed to fetch video information. Please check the URL and try again.');
        }
    }

    displayVideoInfo(data) {
        const videoInfo = document.getElementById('videoInfo');
        
        if (data.type === 'video') {
            this.displaySingleVideo(data);
        } else if (data.type === 'playlist') {
            this.displayPlaylist(data);
        }

        videoInfo.classList.remove('d-none');
        videoInfo.classList.add('fade-in');
    }

    displaySingleVideo(data) {
        const singleVideoInfo = document.getElementById('singleVideoInfo');
        
        // Update video details
        document.getElementById('videoThumbnail').src = data.thumbnail || '';
        document.getElementById('videoTitle').textContent = data.title || 'Unknown Title';
        document.getElementById('videoUploader').textContent = data.uploader || 'Unknown Uploader';
        document.getElementById('videoViews').textContent = this.formatNumber(data.view_count);
        document.getElementById('videoDuration').textContent = this.formatDuration(data.duration);
        document.getElementById('videoDescription').textContent = data.description || 'No description available.';

        // Update quality options
        const qualitySelect = document.getElementById('videoQuality');
        qualitySelect.innerHTML = '<option value="best">Best Available</option>';
        
        if (data.formats && data.formats.length > 0) {
            // Group formats by type
            const videoFormats = data.formats.filter(f => f.type === 'video');
            const audioFormats = data.formats.filter(f => f.type === 'audio');
            
            // Add video formats
            if (videoFormats.length > 0) {
                const videoGroup = document.createElement('optgroup');
                videoGroup.label = 'Video Quality';
                videoFormats.forEach(format => {
                    const option = document.createElement('option');
                    option.value = format.quality;
                    option.textContent = `${format.quality} (${format.ext.toUpperCase()})${format.filesize ? ' - ' + this.formatFileSize(format.filesize) : ''}`;
                    videoGroup.appendChild(option);
                });
                qualitySelect.appendChild(videoGroup);
            }
            
            // Add audio formats
            if (audioFormats.length > 0) {
                const audioGroup = document.createElement('optgroup');
                audioGroup.label = 'Audio Only (MP3)';
                audioFormats.forEach(format => {
                    const option = document.createElement('option');
                    option.value = format.quality;
                    option.textContent = `${format.quality} MP3${format.filesize ? ' - ' + this.formatFileSize(format.filesize) : ''}`;
                    audioGroup.appendChild(option);
                });
                qualitySelect.appendChild(audioGroup);
            }
        }

        singleVideoInfo.classList.remove('d-none');
        singleVideoInfo.classList.add('slide-up');
    }

    displayPlaylist(data) {
        const playlistInfo = document.getElementById('playlistInfo');
        
        // Update playlist details
        document.getElementById('playlistTitle').textContent = data.title || 'Unknown Playlist';
        document.getElementById('playlistUploader').textContent = data.uploader || 'Unknown Uploader';
        document.getElementById('playlistVideoCount').textContent = data.video_count || 0;

        // Display playlist videos
        const playlistVideos = document.getElementById('playlistVideos');
        playlistVideos.innerHTML = '';

        if (data.videos && data.videos.length > 0) {
            data.videos.forEach((video, index) => {
                const videoCard = this.createVideoCard(video, index);
                playlistVideos.appendChild(videoCard);
            });
        }

        playlistInfo.classList.remove('d-none');
        playlistInfo.classList.add('slide-up');
    }

    createVideoCard(video, index) {
        const col = document.createElement('div');
        col.className = 'col-lg-4 col-md-6 mb-4';

        col.innerHTML = `
            <div class="video-card">
                <img src="${video.thumbnail || ''}" class="video-thumbnail" alt="Video Thumbnail">
                <div class="p-3">
                    <h6 class="fw-bold mb-2" title="${video.title || 'Unknown Title'}">
                        ${(video.title || 'Unknown Title').substring(0, 60)}${(video.title || '').length > 60 ? '...' : ''}
                    </h6>
                    <div class="video-meta">
                        <div class="small text-muted mb-1">
                            <i class="fas fa-user me-1"></i>
                            ${video.uploader || 'Unknown'}
                        </div>
                        <div class="small text-muted mb-1">
                            <i class="fas fa-clock me-1"></i>
                            ${this.formatDuration(video.duration)}
                        </div>
                        <div class="small text-muted">
                            <i class="fas fa-eye me-1"></i>
                            ${this.formatNumber(video.view_count)} views
                        </div>
                    </div>
                </div>
            </div>
        `;

        col.classList.add('fade-in');
        col.style.animationDelay = `${index * 0.1}s`;

        return col;
    }

    async downloadVideo() {
        const url = document.getElementById('urlInput').value.trim();
        const quality = document.getElementById('videoQuality').value;

        if (!url) {
            this.showError('URL is required');
            return;
        }

        try {
            const response = await fetch('/download_video', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url, quality: quality })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Download failed');
            }

            this.currentVideoId = data.video_id;
            this.showDownloadProgress();
            this.startProgressTracking();

        } catch (error) {
            console.error('Download error:', error);
            this.showError(error.message || 'Download failed. Please try again.');
        }
    }

    async downloadPlaylist() {
        const url = document.getElementById('urlInput').value.trim();
        const quality = document.getElementById('playlistQuality').value;

        if (!url) {
            this.showError('URL is required');
            return;
        }

        try {
            const response = await fetch('/download_playlist', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url, quality: quality })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Playlist download failed');
            }

            this.currentPlaylistId = data.playlist_id;
            this.showDownloadProgress();
            this.startProgressTracking();

        } catch (error) {
            console.error('Playlist download error:', error);
            this.showError(error.message || 'Playlist download failed. Please try again.');
        }
    }

    showDownloadProgress() {
        document.getElementById('downloadProgress').classList.remove('d-none');
        document.getElementById('downloadProgress').classList.add('fade-in');
        
        // Reset progress display
        const progressBar = document.getElementById('progressBar');
        progressBar.style.width = '0%';
        progressBar.textContent = '0%';
        
        document.getElementById('downloadSpeed').textContent = '-';
        document.getElementById('downloadETA').textContent = '-';
        document.getElementById('downloadStatus').textContent = 'Starting...';
    }

    startProgressTracking() {
        const trackingId = this.currentVideoId || this.currentPlaylistId;
        
        if (!trackingId) return;

        this.progressInterval = setInterval(async () => {
            try {
                const response = await fetch(`/download_progress/${trackingId}`);
                const progress = await response.json();

                this.updateProgressDisplay(progress);

                if (progress.status === 'finished' || progress.status === 'error') {
                    clearInterval(this.progressInterval);
                    this.progressInterval = null;
                }

            } catch (error) {
                console.error('Progress tracking error:', error);
                clearInterval(this.progressInterval);
                this.progressInterval = null;
            }
        }, 1000);
    }

    updateProgressDisplay(progress) {
        const progressBar = document.getElementById('progressBar');
        const speedElement = document.getElementById('downloadSpeed');
        const etaElement = document.getElementById('downloadETA');
        const statusElement = document.getElementById('downloadStatus');

        const percent = progress.percent || 0;
        progressBar.style.width = `${percent}%`;
        progressBar.textContent = `${Math.round(percent)}%`;

        speedElement.textContent = progress.speed || '-';
        etaElement.textContent = progress.eta || '-';

        switch (progress.status) {
            case 'downloading':
                statusElement.textContent = 'Downloading...';
                progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated bg-info';
                break;
            case 'finished':
                statusElement.textContent = 'Download Complete!';
                progressBar.className = 'progress-bar bg-success';
                progressBar.style.width = '100%';
                progressBar.textContent = '100%';
                
                // Show download link if available
                if (progress.download_url) {
                    this.showSuccessMessage(`Download completed successfully! <a href="${progress.download_url}" class="btn btn-sm btn-outline-success ms-2" download><i class="fas fa-download me-1"></i>Download File</a>`);
                    this.addToDownloadsList(progress.filename, progress.download_url);
                } else {
                    this.showSuccessMessage('Download completed successfully!');
                }
                break;
            case 'error':
                statusElement.textContent = 'Download Failed';
                progressBar.className = 'progress-bar bg-danger';
                this.showError(`Download failed: ${progress.error || 'Unknown error'}`);
                break;
            default:
                statusElement.textContent = 'Starting...';
                break;
        }
    }

    showSuccessMessage(message) {
        // Create and show a success alert
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-success alert-dismissible fade show mt-3';
        alertDiv.innerHTML = `
            <i class="fas fa-check-circle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.getElementById('downloadProgress').appendChild(alertDiv);
        
        // Don't auto-dismiss when there's a download link
        if (!message.includes('download')) {
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 5000);
        }
    }

    addToDownloadsList(filename, downloadUrl) {
        // Create downloads history section if it doesn't exist
        let downloadsSection = document.getElementById('downloadsHistory');
        if (!downloadsSection) {
            downloadsSection = document.createElement('div');
            downloadsSection.id = 'downloadsHistory';
            downloadsSection.className = 'mt-4';
            downloadsSection.innerHTML = `
                <div class="card shadow border-0">
                    <div class="card-header">
                        <h5 class="mb-0">
                            <i class="fas fa-download me-2"></i>
                            Recent Downloads
                        </h5>
                    </div>
                    <div class="card-body">
                        <div id="downloadsList"></div>
                    </div>
                </div>
            `;
            document.getElementById('downloadProgress').parentNode.appendChild(downloadsSection);
        }

        // Add download to the list
        const downloadsList = document.getElementById('downloadsList');
        const downloadItem = document.createElement('div');
        downloadItem.className = 'download-item d-flex justify-content-between align-items-center p-2 border-bottom';
        downloadItem.innerHTML = `
            <div class="download-info">
                <i class="fas fa-file-video me-2 text-primary"></i>
                <span class="filename" title="${filename}">${filename.length > 40 ? filename.substring(0, 40) + '...' : filename}</span>
                <small class="text-muted ms-2">${new Date().toLocaleTimeString()}</small>
            </div>
            <a href="${downloadUrl}" class="btn btn-sm btn-outline-primary" download>
                <i class="fas fa-download me-1"></i>Download
            </a>
        `;
        
        // Add to top of list
        downloadsList.insertBefore(downloadItem, downloadsList.firstChild);
        
        // Keep only last 5 downloads
        while (downloadsList.children.length > 5) {
            downloadsList.removeChild(downloadsList.lastChild);
        }
        
        // Show the recent downloads section
        document.getElementById('recent-downloads').classList.remove('d-none');
    }

    async clearDownloads() {
        try {
            const response = await fetch('/clear_downloads', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                // Clear the downloads list UI
                const downloadsList = document.getElementById('downloads-list');
                if (downloadsList) {
                    downloadsList.innerHTML = '';
                }
                
                // Hide the downloads section
                document.getElementById('recent-downloads').classList.add('d-none');
                
                // Show success message
                this.showTemporaryMessage('All temporary downloads cleared!', 'success');
            } else {
                this.showTemporaryMessage('Failed to clear downloads', 'error');
            }
        } catch (error) {
            console.error('Clear downloads error:', error);
            this.showTemporaryMessage('Failed to clear downloads', 'error');
        }
    }

    clearDownloadsOnLoad() {
        // Auto-clear downloads when page loads (simulating refresh behavior)
        setTimeout(() => {
            this.clearDownloads();
        }, 500);
    }

    showTemporaryMessage(message, type = 'info') {
        const alertDiv = document.createElement('div');
        const alertClass = type === 'error' ? 'alert-danger' : type === 'success' ? 'alert-success' : 'alert-info';
        alertDiv.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 1050; max-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 3000);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new YouTubeDownloader();
});

// Add some utility functions for better UX
document.addEventListener('DOMContentLoaded', () => {
    // Add input validation and formatting
    const urlInput = document.getElementById('urlInput');
    
    urlInput.addEventListener('paste', (e) => {
        setTimeout(() => {
            const url = e.target.value.trim();
            if (url && (url.includes('youtube.com') || url.includes('youtu.be'))) {
                document.getElementById('fetchBtn').classList.add('pulse');
                setTimeout(() => {
                    document.getElementById('fetchBtn').classList.remove('pulse');
                }, 1000);
            }
        }, 100);
    });

    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            document.getElementById('urlForm').dispatchEvent(new Event('submit'));
        }
    });
});
