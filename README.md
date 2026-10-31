🎵 Desktop MBBmusicplayer

A sleek, feature-rich desktop music player built with Python and CustomTkinter, featuring a beautiful dark-mode UI inspired by Apple Music.

✨ Features

Modern UI: Clean, responsive dark mode interface with album art rendering and a persistent bottom player bar.

Built-in YouTube Downloader: Paste a YouTube link to securely download and convert audio in the background (powered by yt-dlp).

Auto-Metadata & Thumbnails: Automatically extracts high-quality YouTube thumbnails and embeds them directly into the MP3 file using FFmpeg.

Playlist Management: Create custom playlists, favorite songs, and manage your library with intuitive right-click context menus.

Smart Search: Seamlessly search your library. Includes built-in Traditional to Simplified Chinese conversion, so searching for "听妈妈的话" will perfectly match "聽媽媽的話".

Safe Storage: User settings and playlists are safely stored in the OS-standard AppData/user directory, ensuring nothing breaks when moving music files.

🛠️ Prerequisites

Before running the app, you must install FFmpeg on your system. The built-in downloader relies on it to convert files and embed album art.

Windows: Download from gyan.dev or install via winget: winget install ffmpeg

macOS: brew install ffmpeg

Linux: sudo apt install ffmpeg

🚀 Installation

Clone the repository:

git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git
cd YOUR_REPOSITORY_NAME


Install the required Python packages:

pip install -r requirements.txt


Run the application:

python mp3.py


🎮 Usage

Click "Open Folder..." on the left sidebar to select your local music directory.

Double-click any song to play, or right-click to add it to a playlist or your favorites.

Click "Download from YT" and paste a video URL to instantly expand your library.

⚠️ Disclaimer

This application is intended for educational purposes and personal use only. Users are solely responsible for ensuring they have the legal right to download and use the audio content they access through this software.

📄 License

This project is licensed under the MIT License. (Note: This project uses mutagen, which is GPL-licensed, and relies on yt-dlp and ffmpeg externally).
