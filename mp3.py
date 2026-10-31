import os
import io
import sys
import json
import math
import queue
import random
import threading
import yt_dlp
import tkinter as tk
import customtkinter as ctk
import pygame
from tkinter import filedialog, messagebox
from mutagen import File
from mutagen.id3 import ID3, APIC
from PIL import Image, ImageDraw, ImageTk


# ============================================================
#  Design tokens (Apple Music, dark)
# ============================================================
class C:
    BG = "#1C1C1E"          # main content
    SIDEBAR = "#262628"
    BAR = "#2C2C2E"         # bottom player bar
    PILL = "#1E1E20"        # now-playing pill
    FIELD = "#3A3A3C"       # search field, secondary buttons
    ROW_ALT = "#212123"
    ROW_HOVER = "#2C2C2E"
    ROW_SEL = "#3A3A3C"
    LINE = "#38383A"
    TEXT = "#FFFFFF"
    SUB = "#8E8E93"
    DIM = "#636366"
    ACCENT = "#FA243C"      # Apple Music red


if sys.platform == "darwin":
    FONT = ".AppleSystemUIFont"
elif sys.platform.startswith("win"):
    FONT = "Segoe UI"
else:
    FONT = "Helvetica"


def F(size, weight="normal"):
    return (FONT, size, weight)


# ============================================================
#  Image helpers (icons are drawn with PIL so they look the
#  same on every OS - no emoji font surprises)
# ============================================================
def draw_icon(name, size, color):
    S = size * 4  # supersample for smooth edges
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    p = lambda x, y: (x * S, y * S)
    lw = max(2, int(S * 0.085))

    if name == "play":
        d.polygon([p(.28, .16), p(.28, .84), p(.86, .50)], fill=color)

    elif name == "pause":
        d.rounded_rectangle((S * .24, S * .18, S * .43, S * .82), radius=int(S * .04), fill=color)
        d.rounded_rectangle((S * .57, S * .18, S * .76, S * .82), radius=int(S * .04), fill=color)

    elif name == "next":
        d.polygon([p(.08, .24), p(.08, .76), p(.50, .50)], fill=color)
        d.polygon([p(.48, .24), p(.48, .76), p(.90, .50)], fill=color)

    elif name == "prev":
        d.polygon([p(.92, .24), p(.92, .76), p(.50, .50)], fill=color)
        d.polygon([p(.52, .24), p(.52, .76), p(.10, .50)], fill=color)

    elif name == "shuffle":
        d.line([p(.08, .30), p(.34, .30), p(.62, .70), p(.76, .70)], fill=color, width=lw, joint="curve")
        d.line([p(.08, .70), p(.34, .70), p(.62, .30), p(.76, .30)], fill=color, width=lw, joint="curve")
        d.polygon([p(.74, .56), p(.74, .84), p(.94, .70)], fill=color)
        d.polygon([p(.74, .16), p(.74, .44), p(.94, .30)], fill=color)

    elif name in ("repeat", "repeat1"):
        d.rounded_rectangle((S * .10, S * .24, S * .90, S * .76), radius=int(S * .14), outline=color, width=lw)
        d.rectangle((S * .50, S * .10, S * .72, S * .38), fill=(0, 0, 0, 0))
        d.rectangle((S * .28, S * .62, S * .50, S * .90), fill=(0, 0, 0, 0))
        d.polygon([p(.50, .12), p(.50, .36), p(.74, .24)], fill=color)
        d.polygon([p(.50, .64), p(.50, .88), p(.26, .76)], fill=color)
        if name == "repeat1":
            d.line([p(.50, .40), p(.50, .62)], fill=color, width=int(lw * .8))
            d.line([p(.43, .45), p(.50, .40)], fill=color, width=int(lw * .8))

    elif name in ("heart", "heart_o"):
        pts = []
        for i in range(240):
            t = 2 * math.pi * i / 240
            x = 16 * math.sin(t) ** 3
            y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
            pts.append((S * (0.5 + x / 38), S * (0.5 - (y + 2.5) / 38)))
        if name == "heart":
            d.polygon(pts, fill=color)
        else:
            d.line(pts + [pts[0]], fill=color, width=lw, joint="curve")

    elif name == "note":
        d.ellipse((S * .18, S * .60, S * .48, S * .86), fill=color)
        d.rectangle((S * .42, S * .16, S * .50, S * .74), fill=color)
        d.polygon([p(.50, .16), p(.80, .30), p(.80, .44), p(.50, .30)], fill=color)

    elif name == "search":
        d.ellipse((S * .12, S * .12, S * .62, S * .62), outline=color, width=lw)
        d.line([p(.54, .54), p(.86, .86)], fill=color, width=lw)

    elif name == "folder":
        d.rounded_rectangle((S * .08, S * .20, S * .42, S * .42), radius=int(S * .05), fill=color)
        d.rounded_rectangle((S * .08, S * .30, S * .92, S * .80), radius=int(S * .07), fill=color)

    elif name.startswith("vol"):
        d.polygon([p(.08, .38), p(.26, .38), p(.48, .18), p(.48, .82), p(.26, .62), p(.08, .62)], fill=color)
        cx, cy = S * .44, S * .5
        radii = {"vol_low": [.24], "vol_high": [.24, .40]}.get(name, [])
        for r in radii:
            d.arc((cx - S * r, cy - S * r, cx + S * r, cy + S * r), -50, 50, fill=color, width=lw)
        if name == "vol_mute":
            d.line([p(.62, .38), p(.86, .62)], fill=color, width=lw)
            d.line([p(.62, .62), p(.86, .38)], fill=color, width=lw)

    return img.resize((size, size), Image.Resampling.LANCZOS)


def round_corners(img, radius):
    img = img.convert("RGBA")
    w, h = img.size
    s = 4
    mask = Image.new("L", (w * s, h * s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=radius * s, fill=255)
    img.putalpha(mask.resize((w, h), Image.Resampling.LANCZOS))
    return img


def square(img, size):
    img = img.convert("RGB")
    w, h = img.size
    m = min(w, h)
    left, top = (w - m) // 2, (h - m) // 2
    img = img.crop((left, top, left + m, top + m))
    return img.resize((size, size), Image.Resampling.LANCZOS)


def placeholder_art(size, radius):
    base = round_corners(Image.new("RGBA", (size, size), "#343436"), radius)
    note = draw_icon("note", int(size * 0.5), "#6E6E73")
    off = (size - note.size[0]) // 2
    base.alpha_composite(note, dest=(off, off))
    return base


# ============================================================
#  Metadata helpers (safe to run in a background thread)
# ============================================================
def extract_art_bytes(path):
    try:
        low = path.lower()
        if low.endswith(".mp3"):
            frames = ID3(path).getall("APIC")
            if frames:
                return frames[0].data
        elif low.endswith(".flac"):
            pics = File(path).pictures
            if pics:
                return pics[0].data
    except Exception:
        pass
    return None


def _tag(audio, key):
    try:
        value = audio.get(key)
        if value:
            return str(value[0]).strip()
    except Exception:
        pass
    return ""


def read_track_info(path):
    name = os.path.splitext(os.path.basename(path))[0]
    info = {
        "path": path, "title": name,
        "artist": "Unknown Artist", "album": "Unknown Album",
        "length": 0, "thumb": None, "photo": None,
    }
    try:
        audio = File(path, easy=True)
        if audio is not None:
            if getattr(audio, "info", None) is not None and hasattr(audio.info, "length"):
                info["length"] = audio.info.length
            info["title"] = _tag(audio, "title") or name
            info["artist"] = _tag(audio, "artist") or info["artist"]
            info["album"] = _tag(audio, "album") or info["album"]
    except Exception:
        pass

    data = extract_art_bytes(path)
    if data:
        try:
            info["thumb"] = round_corners(square(Image.open(io.BytesIO(data)), 40), 5)
        except Exception:
            pass
    return info


def format_time(seconds):
    mins, secs = divmod(int(max(seconds, 0)), 60)
    return f"{mins}:{secs:02}"


def summarize(tracks):
    n = len(tracks)
    text = f"{n} song" + ("" if n == 1 else "s")
    total = int(sum(t["length"] for t in tracks))
    if total > 0:
        hrs, rem = divmod(total, 3600)
        mins = rem // 60
        text += f"  •  {hrs} hr {mins} min" if hrs else f"  •  {max(mins, 1)} min"
    return text


def configure_columns(frame):
    """Shared column layout so the header and every row line up."""
    frame.grid_columnconfigure(0, minsize=62)
    frame.grid_columnconfigure(1, weight=5, uniform="c")
    frame.grid_columnconfigure(2, weight=3, uniform="c")
    frame.grid_columnconfigure(3, weight=3, uniform="c")
    frame.grid_columnconfigure(4, minsize=40)
    frame.grid_columnconfigure(5, minsize=64)


# ============================================================
#  The player
# ============================================================
class MusicPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. Window
        self.title("Music")
        self.geometry("1120x720")
        self.minsize(960, 620)
        self.configure(fg_color=C.BG)
        ctk.set_appearance_mode("dark")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 2. Audio engine & state
        pygame.mixer.init()
        self.current_file = None
        self.song_length = 0
        self.is_playing = False
        self.has_started = False
        self.is_sliding = False
        self.playback_offset = 0

        self.tracks = []            # every track in the library (minus hidden)
        self.track_map = {}         # path -> track dict
        self.queue = []             # paths currently visible = play queue
        self.rows = {}              # path -> row widgets
        self.favorites = []
        self.hidden_tracks = []
        self.last_folder = ""
        self.settings_file = "player_settings.json"

        self.volume = 0.8
        self._pre_mute = 0.8
        self.shuffle = False
        self.repeat = 0             # 0 = off, 1 = all, 2 = one

        self.view = "songs"
        self.search_query = ""
        self.selected = None
        self.loading = False
        self.render_token = 0
        self.scan_token = 0
        self.scan_queue = queue.Queue()
        self._search_job = None
        self._icon_cache = {}

        # artwork placeholders
        self.ph_thumb = ImageTk.PhotoImage(placeholder_art(40, 5))
        self.ph_small = self._ctk_image(placeholder_art(96, 12), 48)
        self.ph_big = self._ctk_image(placeholder_art(420, 20), 210)
        self._art_refs = []

        # 3. UI
        self.setup_player_bar()     # built first so it keeps its space when resized
        self.setup_sidebar()
        self.setup_library_view()

        # 4. Session
        self.load_last_session()

        # 5. Loops & bindings
        self.update_progress()
        self._poll_scan()
        self.bind("<space>", self.on_space)
        self.bind("<Escape>", self.on_escape)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # --------------------------------------------------------
    #  Small helpers
    # --------------------------------------------------------
    @staticmethod
    def _ctk_image(pil_img, size):
        return ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(size, size))

    def icon(self, name, size, color):
        key = (name, size, color)
        if key not in self._icon_cache:
            self._icon_cache[key] = self._ctk_image(draw_icon(name, size * 2, color), size)
        return self._icon_cache[key]

    # --------------------------------------------------------
    #  Sidebar
    # --------------------------------------------------------
    def setup_sidebar(self):
        sb = ctk.CTkFrame(self, fg_color=C.SIDEBAR, corner_radius=0, width=250)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.pack_propagate(False)
        self.sidebar = sb

        # search field
        field = ctk.CTkFrame(sb, fg_color=C.FIELD, corner_radius=8, height=32)
        field.pack(fill="x", padx=16, pady=(22, 16))
        field.pack_propagate(False)
        ctk.CTkLabel(field, text="", image=self.icon("search", 14, C.SUB), width=28).pack(side="left", padx=(8, 0))
        self.search_entry = ctk.CTkEntry(
            field, placeholder_text="Search", border_width=0, fg_color="transparent",
            text_color=C.TEXT, placeholder_text_color=C.SUB, font=F(13), height=30
        )
        self.search_entry.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.search_entry.bind("<KeyRelease>", self.on_search)

        # library section
        ctk.CTkLabel(
            sb, text="Library", font=F(12, "bold"), text_color=C.DIM, anchor="w", height=20
        ).pack(fill="x", padx=22, pady=(0, 4))

        self.nav_buttons = {}
        for key, label, ic in (("songs", "Songs", "note"), ("favorites", "Favorites", "heart")):
            btn = ctk.CTkButton(
                sb, text="  " + label, image=self.icon(ic, 18, C.ACCENT), compound="left",
                anchor="w", height=34, corner_radius=8, fg_color="transparent",
                hover_color="#323234", text_color=C.TEXT, font=F(14),
                command=lambda k=key: self.set_view(k)
            )
            btn.pack(fill="x", padx=12, pady=1)
            self.nav_buttons[key] = btn

        ctk.CTkButton(
            sb, text="  Open Folder…", image=self.icon("folder", 18, C.ACCENT), compound="left",
            anchor="w", height=34, corner_radius=8, fg_color="transparent",
            hover_color="#323234", text_color=C.TEXT, font=F(14),
            command=self.ask_and_load_folder
        ).pack(fill="x", padx=12, pady=(14, 1))

        # album art pane at the bottom (the iTunes classic touch)
        self.side_art = ctk.CTkLabel(
            sb, text="", image=self.ph_big, fg_color="transparent", width=210, height=210
        )
        self.side_art.pack(side="bottom", pady=(0, 22))

        self.update_nav_highlight()

        self.download_btn = ctk.CTkButton(
            self.sidebar, text="⬇️ Download from YT", 
            fg_color="#282828", hover_color="#3E3E3E", font=F(14, "bold"),
            command=self.ask_and_download
        )
        self.download_btn.pack(pady=(0, 10), padx=20, fill="x")

    # --------------------------------------------------------
    #  YouTube Download Logic
    # --------------------------------------------------------
    def ask_and_download(self):
        if not self.last_folder:
            messagebox.showwarning("No Folder", "Please Open Folder first to select where to save songs.")
            return

        dialog = ctk.CTkInputDialog(text="Paste YouTube Link:", title="Download Music")
        url = dialog.get_input()
        
        if url:
            self.subtitle_label.configure(text="Downloading & Converting... Please wait.")
            threading.Thread(target=self._download_worker, args=(url,), daemon=True).start()

    def _download_worker(self, url):
        try:
            # 升级版 yt-dlp 配置：自动抓取并嵌入封面
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(self.last_folder, '%(title)s.%(ext)s'),
                'writethumbnail': True,  # 核心1：强制下载视频的封面图
                'postprocessors': [
                    {
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '0',
                    },
                    {
                        'key': 'EmbedThumbnail',  # 核心2：利用 FFmpeg 把下载的图片强行压进 MP3 文件内部
                    },
                ],
                'quiet': True,
                'noprogress': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            self.after(0, lambda: self.scan_folder(self.last_folder))
            self.after(0, lambda: messagebox.showinfo("Success", "Download & Conversion Complete!"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Download Error", str(e)))
            self.after(0, lambda: self.refresh_view())  

    def update_nav_highlight(self):
        for key, btn in self.nav_buttons.items():
            btn.configure(fg_color=C.FIELD if key == self.view else "transparent")

    # --------------------------------------------------------
    #  Library view (header + column titles + song rows)
    # --------------------------------------------------------
    def setup_library_view(self):
        main = ctk.CTkFrame(self, fg_color=C.BG, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)
        main.bind("<Button-1>", lambda e: self.focus_set())
        self.main = main

        # title + action buttons
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(26, 14))
        header.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(header, text="Songs", font=F(32, "bold"), text_color=C.TEXT, anchor="w")
        self.title_label.grid(row=0, column=0, sticky="w")
        self.subtitle_label = ctk.CTkLabel(header, text="", font=F(13), text_color=C.SUB, anchor="w")
        self.subtitle_label.grid(row=1, column=0, sticky="w")

        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.grid(row=0, column=1, rowspan=2, sticky="e")
        for text, ic, cmd in (("Play", "play", self.play_all), ("Shuffle", "shuffle", self.shuffle_all)):
            ctk.CTkButton(
                actions, text="  " + text, image=self.icon(ic, 15, C.ACCENT), compound="left",
                width=100, height=34, corner_radius=8, fg_color=C.FIELD, hover_color="#4A4A4C",
                text_color=C.ACCENT, font=F(14, "bold"), command=cmd
            ).pack(side="left", padx=(8, 0))

        # column titles
        colhead = tk.Frame(self.main, bg=C.BG, height=30, bd=0, highlightthickness=0)
        colhead.grid(row=1, column=0, sticky="ew", padx=(20, 26))
        colhead.grid_propagate(False)
        colhead.grid_rowconfigure(0, weight=1)
        configure_columns(colhead)
        for col, text, anchor, padx in (
            (1, "Song", "w", (12, 8)), (2, "Artist", "w", (0, 8)),
            (3, "Album", "w", (0, 8)), (5, "Time", "e", (0, 12)),
        ):
            tk.Label(
                colhead, text=text, font=F(11, "bold"), fg=C.SUB, bg=C.BG, anchor=anchor, width=1
            ).grid(row=0, column=col, sticky="ew", padx=padx)
        tk.Frame(self.main, bg=C.LINE, height=1).grid(row=1, column=0, sticky="sew", padx=(28, 30))

        # scrolling list
        self.list_frame = ctk.CTkScrollableFrame(
            self.main, fg_color="transparent", corner_radius=0,
            scrollbar_button_color="#3A3A3C", scrollbar_button_hover_color="#5A5A5C"
        )
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=(20, 4), pady=(2, 0))

    # --------------------------------------------------------
    #  Bottom player bar
    # --------------------------------------------------------
    def setup_player_bar(self):
        ctk.CTkFrame(self, fg_color=C.LINE, corner_radius=0, height=1).grid(
            row=1, column=0, columnspan=2, sticky="ew")

        bar = ctk.CTkFrame(self, fg_color=C.BAR, corner_radius=0, height=96)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_rowconfigure(0, weight=1)
        bar.grid_columnconfigure(0, minsize=270)
        bar.grid_columnconfigure(1, weight=1)
        bar.grid_columnconfigure(2, minsize=270)

        # --- transport controls (left)
        transport = ctk.CTkFrame(bar, fg_color="transparent")
        transport.grid(row=0, column=0, sticky="w", padx=(22, 0))

        def tbtn(size_icon, cmd, name, color=C.TEXT):
            b = ctk.CTkButton(
                transport, text="", image=self.icon(name, size_icon, color), width=42, height=42,
                corner_radius=21, fg_color="transparent", hover_color="#3A3A3C", command=cmd
            )
            b.pack(side="left", padx=1)
            return b

        self.shuffle_btn = tbtn(18, self.toggle_shuffle, "shuffle", C.SUB)
        self.prev_btn = tbtn(22, self.prev_track, "prev")
        self.play_btn = tbtn(30, self.play_pause_track, "play")
        self.next_btn = tbtn(22, self.next_track, "next")
        self.repeat_btn = tbtn(18, self.toggle_repeat, "repeat", C.SUB)

        # --- now-playing pill (center)
        pill = ctk.CTkFrame(bar, fg_color=C.PILL, corner_radius=10, height=74)
        pill.grid(row=0, column=1, sticky="ew", padx=16)
        pill.grid_propagate(False)
        pill.grid_columnconfigure(1, weight=1)
        pill.grid_rowconfigure(0, weight=1)

        self.np_art = ctk.CTkLabel(pill, text="", image=self.ph_small, width=48, height=48, fg_color="transparent")
        self.np_art.grid(row=0, column=0, padx=(12, 0))

        info = ctk.CTkFrame(pill, fg_color="transparent")
        info.grid(row=0, column=1, sticky="ew", padx=(12, 16))
        info.grid_columnconfigure(0, weight=1)

        self.np_title = ctk.CTkLabel(info, text="Not Playing", font=F(13, "bold"), text_color=C.TEXT, height=18)
        self.np_title.grid(row=0, column=0)
        self.np_sub = ctk.CTkLabel(info, text="", font=F(12), text_color=C.SUB, height=16)
        self.np_sub.grid(row=1, column=0)

        prog = ctk.CTkFrame(info, fg_color="transparent")
        prog.grid(row=2, column=0, sticky="ew", pady=(2, 0))
        self.time_current = ctk.CTkLabel(prog, text="0:00", font=F(10), text_color=C.SUB, width=38, height=14, anchor="w")
        self.time_current.pack(side="left")
        self.time_total = ctk.CTkLabel(prog, text="-0:00", font=F(10), text_color=C.SUB, width=38, height=14, anchor="e")
        self.time_total.pack(side="right")
        self.progress_slider = ctk.CTkSlider(
            prog, from_=0, to=100, height=14, border_width=5,
            fg_color="#4A4A4C", progress_color="#D1D1D6",
            button_color="#FFFFFF", button_hover_color="#FFFFFF",
            command=self.on_slider_move
        )
        self.progress_slider.set(0)
        self.progress_slider.pack(side="left", fill="x", expand=True, padx=6)
        self.progress_slider.bind("<Button-1>", self.on_slider_press)
        self.progress_slider.bind("<ButtonRelease-1>", self.on_slider_release)

        # --- volume (right)
        vol = ctk.CTkFrame(bar, fg_color="transparent")
        vol.grid(row=0, column=2, sticky="e", padx=(0, 28))
        self.vol_btn = ctk.CTkButton(
            vol, text="", image=self.icon("vol_high", 18, C.SUB), width=30, height=30,
            corner_radius=15, fg_color="transparent", hover_color="#3A3A3C", command=self.toggle_mute
        )
        self.vol_btn.pack(side="left")
        self.volume_slider = ctk.CTkSlider(
            vol, from_=0, to=1, width=110, height=12, border_width=4,
            fg_color="#4A4A4C", progress_color="#D1D1D6",
            button_color="#FFFFFF", button_hover_color="#FFFFFF",
            command=lambda v: self.apply_volume(v, update_slider=False)
        )
        self.volume_slider.pack(side="left", padx=(4, 0))

    # --------------------------------------------------------
    #  Persistence
    # --------------------------------------------------------
    def load_last_session(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    data = json.load(f)
                self.favorites = data.get("favorites", [])
                self.hidden_tracks = data.get("hidden_tracks", [])
                self.last_folder = data.get("last_folder", "")
                self.volume = float(data.get("volume", 0.8))
                self.shuffle = bool(data.get("shuffle", False))
                self.repeat = int(data.get("repeat", 0))
            except Exception:
                pass

        self.apply_volume(self.volume)
        self.update_mode_buttons()

        if self.last_folder and os.path.isdir(self.last_folder):
            self.scan_folder(self.last_folder)
        else:
            self.refresh_view()

    def save_session(self):
        try:
            data = {
                "last_folder": self.last_folder,
                "favorites": self.favorites,
                "hidden_tracks": self.hidden_tracks,
                "volume": self.volume,
                "shuffle": self.shuffle,
                "repeat": self.repeat,
            }
            with open(self.settings_file, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def on_close(self):
        self.save_session()
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        self.destroy()

    # --------------------------------------------------------
    #  Folder scanning (tags are read in a background thread)
    # --------------------------------------------------------
    def ask_and_load_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.last_folder = folder_path
            self.save_session()
            self.scan_folder(folder_path)

    def scan_folder(self, folder_path):
        valid_formats = (".mp3", ".ogg", ".wav", ".flac")
        files = []
        for name in sorted(os.listdir(folder_path), key=str.lower):
            if name.lower().endswith(valid_formats):
                full = os.path.join(folder_path, name)
                if full not in self.hidden_tracks:
                    files.append(full)

        self.scan_token += 1
        token = self.scan_token
        self.loading = True
        self.refresh_view()

        def worker():
            result = [read_track_info(p) for p in files]
            self.scan_queue.put((token, result))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_scan(self):
        try:
            while True:
                token, result = self.scan_queue.get_nowait()
                if token == self.scan_token:
                    self.tracks = result
                    self.track_map = {t["path"]: t for t in result}
                    self.loading = False
                    self.refresh_view(reset_scroll=True)
        except queue.Empty:
            pass
        self.after(100, self._poll_scan)

    # --------------------------------------------------------
    #  Views, search and rendering
    # --------------------------------------------------------
    def set_view(self, key):
        self.view = key
        self.update_nav_highlight()
        self.refresh_view(reset_scroll=True)

    def on_search(self, event=None):
        query = self.search_entry.get().strip()
        if query == self.search_query:
            return
        self.search_query = query
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(180, lambda: self.refresh_view(reset_scroll=True))

    def on_escape(self, event=None):
        if self.search_entry.get():
            self.search_entry.delete(0, "end")
            self.search_query = ""
            self.refresh_view(reset_scroll=True)
        self.focus_set()

    def refresh_view(self, reset_scroll=False):
        items = self.tracks
        if self.view == "favorites":
            items = [t for t in items if t["path"] in self.favorites]
        q = self.search_query.lower()
        if q:
            items = [t for t in items
                     if q in t["title"].lower() or q in t["artist"].lower() or q in t["album"].lower()]

        self.queue = [t["path"] for t in items]
        self.title_label.configure(text="Favorites" if self.view == "favorites" else "Songs")
        self.subtitle_label.configure(text="Loading…" if self.loading else summarize(items))
        self.render_rows(items)
        if reset_scroll:
            self.scroll_top()

    def scroll_top(self):
        try:
            self.list_frame._parent_canvas.yview_moveto(0)
        except Exception:
            pass

    def render_rows(self, items):
        self.render_token += 1
        for w in self.list_frame.winfo_children():
            w.destroy()
        self.rows = {}

        if not items:
            self.show_empty_state()
            return
        self._render_batch(items, 0, self.render_token)

    def _render_batch(self, items, start, token):
        if token != self.render_token:
            return
        end = min(start + 40, len(items))
        for i in range(start, end):
            self.build_row(i, items[i])
        if end < len(items):
            self.after(5, lambda: self._render_batch(items, end, token))

    def show_empty_state(self):
        if self.loading:
            title, msg, button = "Loading Music…", "Reading your library.", False
        elif self.search_query:
            title, msg, button = "No Results", f"Nothing matches “{self.search_query}”.", False
        elif self.view == "favorites":
            title, msg, button = "No Favorites", "Click the heart next to a song, or right-click it, to add it here.", False
        else:
            title, msg, button = "No Music", "Choose a folder to build your library.", True

        box = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        box.pack(pady=(110, 0))
        ctk.CTkLabel(box, text="", image=self.icon("note", 44, C.DIM)).pack(pady=(0, 10))
        ctk.CTkLabel(box, text=title, font=F(20, "bold"), text_color=C.TEXT).pack()
        ctk.CTkLabel(box, text=msg, font=F(13), text_color=C.SUB).pack(pady=(4, 16))
        if button:
            ctk.CTkButton(
                box, text="Open Folder…", width=140, height=36, corner_radius=8,
                fg_color=C.ACCENT, hover_color="#E01F35", text_color="white",
                font=F(14, "bold"), command=self.ask_and_load_folder
            ).pack()

    # --------------------------------------------------------
    #  Song rows
    # --------------------------------------------------------
    def build_row(self, index, track):
        path = track["path"]
        base = C.BG if index % 2 == 0 else C.ROW_ALT

        frame = tk.Frame(self.list_frame, bg=base, height=52, bd=0, highlightthickness=0)
        frame.pack(fill="x")
        frame.grid_propagate(False)
        frame.grid_rowconfigure(0, weight=1)
        configure_columns(frame)

        if track.get("photo") is None and track.get("thumb") is not None:
            track["photo"] = ImageTk.PhotoImage(track["thumb"])
        photo = track.get("photo") or self.ph_thumb

        art = tk.Label(frame, image=photo, bg=base, bd=0)
        art.grid(row=0, column=0, padx=(10, 0))

        def cell(col, text, fg, anchor="w", padx=(0, 8)):
            lbl = tk.Label(frame, text=text, font=F(13), fg=fg, bg=base, anchor=anchor, width=1)
            lbl.grid(row=0, column=col, sticky="ew", padx=padx)
            return lbl

        title = cell(1, track["title"], C.TEXT, padx=(12, 8))
        artist = cell(2, track["artist"], C.SUB)
        album = cell(3, track["album"], C.SUB)
        heart = tk.Label(frame, text="", font=F(13), fg=C.ACCENT, bg=base, bd=0, width=2)
        heart.grid(row=0, column=4)
        length = cell(5, format_time(track["length"]), C.SUB, anchor="e", padx=(0, 12))

        self.rows[path] = {
            "frame": frame, "base": base, "hover": False,
            "labels": [art, title, artist, album, heart, length],
            "title": title, "heart": heart, "sub": [artist, album, length],
        }

        right_click = ["<Button-3>"]
        if sys.platform == "darwin":
            right_click += ["<Button-2>", "<Control-Button-1>"]

        for w in (frame, art, title, artist, album, length):
            w.bind("<Button-1>", lambda e, p=path: self.select_row(p))
            w.bind("<Double-Button-1>", lambda e, p=path: self.play_track(p))
            for seq in right_click:
                w.bind(seq, lambda e, p=path: self.show_context_menu(e, p))
        heart.bind("<Button-1>", lambda e, p=path: (self.toggle_favorite(p), "break")[1])
        heart.bind("<Double-Button-1>", lambda e: "break")
        for seq in right_click:
            heart.bind(seq, lambda e, p=path: self.show_context_menu(e, p))

        for w in [frame] + self.rows[path]["labels"]:
            w.bind("<Enter>", lambda e, p=path: self.row_enter(p), add="+")
            w.bind("<Leave>", lambda e, p=path: self.after(15, lambda: self.row_leave_check(p)), add="+")

        self.paint_row(path)

    def paint_row(self, path):
        r = self.rows.get(path)
        if not r or not r["frame"].winfo_exists():
            return
        if path == self.selected:
            bg = C.ROW_SEL
        elif r["hover"]:
            bg = C.ROW_HOVER
        else:
            bg = r["base"]

        r["frame"].configure(bg=bg)
        for w in r["labels"]:
            w.configure(bg=bg)

        playing = path == self.current_file
        r["title"].configure(fg=C.ACCENT if playing else C.TEXT, font=F(13, "bold" if playing else "normal"))

        if path in self.favorites:
            r["heart"].configure(text="♥", fg=C.ACCENT)
        elif r["hover"]:
            r["heart"].configure(text="♡", fg=C.DIM)
        else:
            r["heart"].configure(text="")

    def row_enter(self, path):
        r = self.rows.get(path)
        if r and not r["hover"]:
            r["hover"] = True
            self.paint_row(path)

    def row_leave_check(self, path):
        r = self.rows.get(path)
        if not r or not r["frame"].winfo_exists():
            return
        try:
            w = self.winfo_containing(*self.winfo_pointerxy())
        except Exception:
            w = None
        while w is not None:
            if w is r["frame"]:
                return
            w = getattr(w, "master", None)
        r["hover"] = False
        self.paint_row(path)

    def select_row(self, path):
        self.focus_set()
        old, self.selected = self.selected, path
        self.paint_row(old)
        self.paint_row(path)

    def drop_row(self, path):
        r = self.rows.pop(path, None)
        if r:
            r["frame"].destroy()
        if path in self.queue:
            self.queue.remove(path)
        if not self.rows:
            self.refresh_view()
            return
        for i, (p, row) in enumerate(self.rows.items()):
            row["base"] = C.BG if i % 2 == 0 else C.ROW_ALT
            self.paint_row(p)
        self.subtitle_label.configure(text=summarize([self.track_map[p] for p in self.queue if p in self.track_map]))

    # --------------------------------------------------------
    #  Context menu / favorites / remove
    # --------------------------------------------------------
    def show_context_menu(self, event, path):
        self.select_row(path)
        menu = tk.Menu(
            self, tearoff=0, bg="#2C2C2E", fg="white", bd=0,
            activebackground=C.ACCENT, activeforeground="white", font=F(11)
        )
        menu.add_command(label="Play", command=lambda: self.play_track(path))
        menu.add_separator()
        if path in self.favorites:
            menu.add_command(label="Remove from Favorites", command=lambda: self.toggle_favorite(path))
        else:
            menu.add_command(label="Add to Favorites", command=lambda: self.toggle_favorite(path))
        menu.add_separator()
        menu.add_command(label="Remove from Library", command=lambda: self.remove_track_from_app(path))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def toggle_favorite(self, path):
        if path in self.favorites:
            self.favorites.remove(path)
            if self.view == "favorites":
                self.drop_row(path)
        else:
            self.favorites.append(path)
        self.paint_row(path)
        self.save_session()

    def remove_track_from_app(self, path):
        track = self.track_map.get(path)
        name = track["title"] if track else os.path.basename(path)
        confirm = messagebox.askyesno(
            "Remove from Library",
            f"Remove this song from your library?\n(The file on your PC will NOT be deleted)\n\n{name}"
        )
        if not confirm:
            return

        if self.current_file == path:
            self.stop_playback()
            self.current_file = None
            self.clear_now_playing()

        if path not in self.hidden_tracks:
            self.hidden_tracks.append(path)
        if path in self.favorites:
            self.favorites.remove(path)
        self.tracks = [t for t in self.tracks if t["path"] != path]
        self.track_map.pop(path, None)
        if self.selected == path:
            self.selected = None

        self.drop_row(path)
        self.save_session()

    # --------------------------------------------------------
    #  Now playing display
    # --------------------------------------------------------
    def update_now_playing(self, track):
        self.np_title.configure(text=track["title"])
        sub = track["artist"]
        if track["album"] and track["album"] != "Unknown Album":
            sub += f" — {track['album']}"
        self.np_sub.configure(text=sub)

        small, big = self.ph_small, self.ph_big
        data = extract_art_bytes(track["path"])
        if data:
            try:
                src = Image.open(io.BytesIO(data))
                small = self._ctk_image(round_corners(square(src, 96), 12), 48)
                big = self._ctk_image(round_corners(square(src, 420), 20), 210)
            except Exception:
                pass
        self._art_refs = [small, big]
        self.np_art.configure(image=small)
        self.side_art.configure(image=big)

    def clear_now_playing(self):
        self.np_title.configure(text="Not Playing")
        self.np_sub.configure(text="")
        self.np_art.configure(image=self.ph_small)
        self.side_art.configure(image=self.ph_big)
        self.progress_slider.set(0)
        self.time_current.configure(text="0:00")
        self.time_total.configure(text="-0:00")
        self._art_refs = []

    # --------------------------------------------------------
    #  Playback
    # --------------------------------------------------------
    def play_track(self, path):
        track = self.track_map.get(path)
        if not track:
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
        except pygame.error as e:
            messagebox.showerror("Can't play this song", f"{os.path.basename(path)}\n\n{e}")
            return

        old, self.current_file = self.current_file, path
        self.selected = path
        self.is_playing = True
        self.has_started = True
        self.playback_offset = 0
        self.song_length = track["length"]

        self.progress_slider.configure(to=max(self.song_length, 1))
        self.progress_slider.set(0)
        self.time_current.configure(text="0:00")
        self.time_total.configure(text="-" + format_time(self.song_length))
        self.update_now_playing(track)
        self.play_btn.configure(image=self.icon("pause", 30, C.TEXT))

        self.paint_row(old)
        self.paint_row(path)

    def play_pause_track(self):
        if not self.current_file:
            if self.queue:
                self.play_track(self.selected if self.selected in self.queue else self.queue[0])
            return

        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.play_btn.configure(image=self.icon("play", 30, C.TEXT))
        else:
            if self.has_started:
                pygame.mixer.music.unpause()
            else:
                try:
                    pygame.mixer.music.load(self.current_file)
                    pygame.mixer.music.play()
                except pygame.error:
                    return
                self.has_started = True
                self.playback_offset = 0
            self.is_playing = True
            self.play_btn.configure(image=self.icon("pause", 30, C.TEXT))

    def stop_playback(self):
        pygame.mixer.music.stop()
        self.is_playing = False
        self.has_started = False
        self.playback_offset = 0
        self.play_btn.configure(image=self.icon("play", 30, C.TEXT))
        self.progress_slider.set(0)
        self.time_current.configure(text="0:00")
        self.time_total.configure(text="-" + format_time(self.song_length))

    def current_position(self):
        return self.playback_offset + max(pygame.mixer.music.get_pos(), 0) / 1000

    def next_track(self, auto=False):
        if not self.queue:
            return
        if auto and self.repeat == 2 and self.current_file:
            self.play_track(self.current_file)
            return
        if self.shuffle and len(self.queue) > 1:
            self.play_track(random.choice([p for p in self.queue if p != self.current_file]))
            return

        if self.current_file in self.queue:
            i = self.queue.index(self.current_file) + 1
            if i >= len(self.queue):
                if self.repeat == 1 or not auto:
                    i = 0
                else:
                    self.stop_playback()
                    return
        else:
            i = 0
        self.play_track(self.queue[i])

    def prev_track(self):
        if not self.queue:
            return
        if self.current_file and self.has_started and self.current_position() > 3:
            self.play_track(self.current_file)   # restart, like most players
            return
        if self.current_file in self.queue:
            i = (self.queue.index(self.current_file) - 1) % len(self.queue)
        else:
            i = 0
        self.play_track(self.queue[i])

    def play_all(self):
        if self.queue:
            self.play_track(self.queue[0])

    def shuffle_all(self):
        if self.queue:
            self.shuffle = True
            self.update_mode_buttons()
            self.save_session()
            self.play_track(random.choice(self.queue))

    def toggle_shuffle(self):
        self.shuffle = not self.shuffle
        self.update_mode_buttons()
        self.save_session()

    def toggle_repeat(self):
        self.repeat = (self.repeat + 1) % 3
        self.update_mode_buttons()
        self.save_session()

    def update_mode_buttons(self):
        self.shuffle_btn.configure(
            image=self.icon("shuffle", 18, C.ACCENT if self.shuffle else C.SUB),
            fg_color="#3A3A3C" if self.shuffle else "transparent")
        name = "repeat1" if self.repeat == 2 else "repeat"
        self.repeat_btn.configure(
            image=self.icon(name, 18, C.ACCENT if self.repeat else C.SUB),
            fg_color="#3A3A3C" if self.repeat else "transparent")

    # --------------------------------------------------------
    #  Seek bar & progress loop
    # --------------------------------------------------------
    def on_slider_press(self, event):
        self.is_sliding = True

    def on_slider_move(self, value):
        self.time_current.configure(text=format_time(value))
        self.time_total.configure(text="-" + format_time(self.song_length - value))

    def on_slider_release(self, event):
        if not self.current_file:
            self.progress_slider.set(0)
            self.is_sliding = False
            return

        jump = self.progress_slider.get()
        try:
            pygame.mixer.music.play(start=jump)
            self.playback_offset = jump
            self.has_started = True
            if not self.is_playing:
                pygame.mixer.music.pause()
        except pygame.error:
            pass   # some formats (e.g. wav) can't seek

        self.on_slider_move(jump)
        self.is_sliding = False

    def update_progress(self):
        if self.is_playing and self.has_started:
            if pygame.mixer.music.get_busy():
                if not self.is_sliding and self.song_length > 0:
                    t = min(self.current_position(), self.song_length)
                    self.progress_slider.set(t)
                    self.on_slider_move(t)
            else:
                self.on_track_end()
        self.after(250, self.update_progress)

    def on_track_end(self):
        self.next_track(auto=True)

    # --------------------------------------------------------
    #  Volume
    # --------------------------------------------------------
    def apply_volume(self, value, update_slider=True):
        self.volume = float(value)
        pygame.mixer.music.set_volume(self.volume)
        if update_slider:
            self.volume_slider.set(self.volume)
        name = "vol_mute" if self.volume <= 0.001 else "vol_low" if self.volume < 0.5 else "vol_high"
        self.vol_btn.configure(image=self.icon(name, 18, C.SUB))

    def toggle_mute(self):
        if self.volume > 0.001:
            self._pre_mute = self.volume
            self.apply_volume(0)
        else:
            self.apply_volume(self._pre_mute or 0.8)

    # --------------------------------------------------------
    #  Keyboard
    # --------------------------------------------------------
    def on_space(self, event):
        try:
            if isinstance(self.focus_get(), tk.Entry):
                return None    # let the search box receive the space
        except Exception:
            pass
        self.play_pause_track()
        return "break"


if __name__ == "__main__":
    app = MusicPlayer()
    app.mainloop()