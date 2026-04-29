import os
import shutil
import threading
import subprocess

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.core.window import Window

# ===============================
# Android path fallback
# ===============================
try:
    from android.storage import app_storage_path
    APP_HOME = app_storage_path()
except:
    APP_HOME = "/data/data/org.m4s.convert/files/app"

SCAN_DIR = "/storage/emulated/0/Download"

FFMPEG_DIR = os.path.join(APP_HOME, "ffmpeg_libs")
FFMPEG_BIN = os.path.join(FFMPEG_DIR, "ffmpeg")


# ===============================
# ffmpeg deploy
# ===============================
def find_source_ffmpeg():
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "ffmpeg_libs")

    if os.path.isfile(os.path.join(path, "ffmpeg")):
        return path
    return None


def deploy_ffmpeg():
    try:
        if os.path.isfile(FFMPEG_BIN):
            os.chmod(FFMPEG_BIN, 0o755)
            return True, ""
    except:
        pass

    src = find_source_ffmpeg()

    if not src:
        return False, "ffmpeg_libs folder not found."

    try:
        os.makedirs(FFMPEG_DIR, exist_ok=True)

        for f in os.listdir(src):
            s = os.path.join(src, f)
            d = os.path.join(FFMPEG_DIR, f)

            if os.path.isfile(s):
                shutil.copy2(s, d)
                os.chmod(d, 0o755)

        return True, ""

    except Exception as e:
        return False, str(e)


# ===============================
# tools
# ===============================
def readable_size(path):
    try:
        size = os.path.getsize(path)
        return f"{size / 1024 / 1024:.1f}MB"
    except:
        return "?"


def safe_output_name(src_path, bitrate):
    base = src_path.rsplit(".", 1)[0]
    out = f"{base}({bitrate}).mp3"

    if not os.path.exists(out):
        return out

    n = 2
    while True:
        out = f"{base}({bitrate})_{n}.mp3"
        if not os.path.exists(out):
            return out
        n += 1


# ===============================
# row widget
# ===============================
class FileRow(BoxLayout):
    def __init__(self, full_path, filename, callback):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=85,
            spacing=10
        )

        self.full_path = full_path
        self.selected = False
        self.callback = callback

        self.label = Label(
            text=filename,
            font_size=20,
            halign="left",
            valign="middle",
            size_hint_x=0.66,
            color=(1, 1, 1, 1)
        )
        self.label.bind(size=self.label.setter("text_size"))

        self.btn = Button(
            text="Choose",
            font_size=20,
            size_hint_x=0.34,
            background_color=(0.1, 0.6, 0.2, 1)
        )
        self.btn.bind(on_press=self.press)

        self.add_widget(self.label)
        self.add_widget(self.btn)

    def press(self, instance):
        self.callback(self)

    def set_selected(self, state):
        self.selected = state

        if state:
            self.btn.text = "Selected"
            self.btn.background_color = (0.8, 0.2, 0.2, 1)
            self.label.color = (1, 0.9, 0.2, 1)
        else:
            self.btn.text = "Choose"
            self.btn.background_color = (0.1, 0.6, 0.2, 1)
            self.label.color = (1, 1, 1, 1)


# ===============================
# app
# ===============================
class ConverterApp(App):

    def build(self):
        Window.clearcolor = (0.12, 0.13, 0.16, 1)
        self.title = "M4S To MP3"

        self.rows = []
        self.selected = []
        self.running = False

        self.bitrate = "192k"
        self.rate_buttons = []

        ok, err = deploy_ffmpeg()

        if not ok:
            return Label(
                text=err,
                font_size=22,
                color=(1, 0.2, 0.2, 1)
            )

        os.environ["LD_LIBRARY_PATH"] = FFMPEG_DIR

        root = BoxLayout(
            orientation="vertical",
            padding=12,
            spacing=8
        )

        # title
        root.add_widget(Label(
            text="M4S TO MP3",
            font_size=32,
            bold=True,
            size_hint_y=None,
            height=55
        ))

        # status
        self.status = Label(
            text="Scanning...",
            font_size=20,
            size_hint_y=None,
            height=30
        )
        root.add_widget(self.status)

        # progress
        self.progress = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=18
        )
        root.add_widget(self.progress)

        # file list
        scroll = ScrollView(size_hint_y=0.48)

        self.box = BoxLayout(
            orientation="vertical",
            spacing=8,
            size_hint_y=None
        )
        self.box.bind(minimum_height=self.box.setter("height"))

        scroll.add_widget(self.box)
        root.add_widget(scroll)

        # bitrate buttons
        rate_bar = BoxLayout(
            size_hint_y=None,
            height=58,
            spacing=8
        )

        for rate in ["128k", "192k", "256k", "320k"]:
            btn = Button(
                text=rate,
                font_size=18
            )
            btn.bind(on_press=lambda x, r=rate: self.set_rate(r))
            self.rate_buttons.append(btn)
            rate_bar.add_widget(btn)

        root.add_widget(rate_bar)
        self.refresh_rate_buttons()

        # action buttons
        bottom = BoxLayout(
            size_hint_y=None,
            height=68,
            spacing=8
        )

        self.select_btn = Button(
            text="All",
            font_size=20,
            size_hint_x=0.20,
            background_color=(0.2, 0.45, 0.8, 1)
        )
        self.select_btn.bind(on_press=lambda x: self.select_all())

        self.clear_btn = Button(
            text="None",
            font_size=20,
            size_hint_x=0.20,
            background_color=(0.45, 0.45, 0.45, 1)
        )
        self.clear_btn.bind(on_press=lambda x: self.clear_all())

        self.convert_btn = Button(
            text="Convert",
            font_size=22,
            size_hint_x=0.60,
            background_color=(0.75, 0.12, 0.12, 1)
        )
        self.convert_btn.bind(on_press=lambda x: self.start())

        bottom.add_widget(self.select_btn)
        bottom.add_widget(self.clear_btn)
        bottom.add_widget(self.convert_btn)

        root.add_widget(bottom)

        # log area (no Select All popup)
        self.logbox = Label(
            text="",
            font_size=16,
            halign="left",
            valign="top",
            size_hint_y=None,
            color=(1, 1, 1, 1)
        )

        self.logbox.bind(
            width=lambda s, w: setattr(s, "text_size", (w, None)),
            texture_size=lambda s, v: setattr(s, "height", v[1])
        )

        log_scroll = ScrollView(size_hint_y=0.25)
        log_scroll.add_widget(self.logbox)

        root.add_widget(log_scroll)

        self.scan()
        return root

    # ==========================
    # ui tools
    # ==========================
    def set_rate(self, rate):
        self.bitrate = rate
        self.refresh_rate_buttons()

    def refresh_rate_buttons(self):
        for btn in self.rate_buttons:
            if btn.text == self.bitrate:
                btn.background_color = (0.9, 0.6, 0.1, 1)
            else:
                btn.background_color = (0.35, 0.35, 0.35, 1)

    def log(self, txt):
        self.logbox.text += txt + "\n"

    # ==========================
    # scan
    # ==========================
    def scan(self):
        self.rows.clear()
        self.selected.clear()
        self.box.clear_widgets()
        self.progress.value = 0
        self.logbox.text = ""

        if not os.path.isdir(SCAN_DIR):
            self.status.text = "Download missing"
            return

        files = []

        for f in sorted(os.listdir(SCAN_DIR)):
            if f.lower().endswith(".m4s"):
                files.append(f)

        if not files:
            self.status.text = "No m4s found"
            return

        for name in files:
            path = os.path.join(SCAN_DIR, name)
            row = FileRow(path, name, self.toggle_row)

            self.rows.append(row)
            self.box.add_widget(row)

        self.status.text = f"Found {len(files)} files"

    # ==========================
    # choose
    # ==========================
    def toggle_row(self, row):
        row.set_selected(not row.selected)

        if row.selected:
            if row.full_path not in self.selected:
                self.selected.append(row.full_path)
        else:
            if row.full_path in self.selected:
                self.selected.remove(row.full_path)

    def select_all(self):
        self.selected.clear()

        for r in self.rows:
            r.set_selected(True)
            self.selected.append(r.full_path)

    def clear_all(self):
        self.selected.clear()

        for r in self.rows:
            r.set_selected(False)

    # ==========================
    # convert
    # ==========================
    def start(self):
        if self.running:
            return

        if not self.selected:
            self.log("Please choose file.")
            return

        self.running = True
        self.convert_btn.disabled = True
        self.select_btn.disabled = True
        self.clear_btn.disabled = True
        self.progress.value = 0

        threading.Thread(
            target=self.work,
            daemon=True
        ).start()

    def work(self):
        ok = 0
        bad = 0

        total = len(self.selected)
        bitrate = self.bitrate

        for idx, src in enumerate(self.selected):

            name = os.path.basename(src)
            out = safe_output_name(src, bitrate)
            out_name = os.path.basename(out)

            percent = int(((idx + 1) / total) * 100)

            Clock.schedule_once(
                lambda dt, i=idx + 1, t=total, p=percent:
                self.update_progress(i, t, p)
            )

            Clock.schedule_once(
                lambda dt, nm=name:
                self.log(f"Changing-{nm}")
            )

            cmd = [
                FFMPEG_BIN,
                "-i", src,
                "-vn",
                "-acodec", "libmp3lame",
                "-ab", bitrate,
                "-y",
                out
            ]

            try:
                r = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                if r.returncode == 0 and os.path.exists(out):
                    ok += 1
                    size = readable_size(out)

                    Clock.schedule_once(
                        lambda dt, nm=out_name, sz=size:
                        self.log(f"Success-{nm}[{sz}]")
                    )
                else:
                    bad += 1
                    Clock.schedule_once(
                        lambda dt, nm=name:
                        self.log(f"Fail-{nm}")
                    )

            except:
                bad += 1
                Clock.schedule_once(
                    lambda dt, nm=name:
                    self.log(f"Fail-{nm}")
                )

        Clock.schedule_once(
            lambda dt: self.finish(ok, bad)
        )

    def update_progress(self, n, total, percent):
        self.status.text = f"{n}/{total}"
        self.progress.value = percent

    def finish(self, ok, bad):
        self.running = False

        self.progress.value = 100
        self.status.text = "Finished"

        self.log("----------------")
        self.log("Finished")
        self.log(f"Success: {ok}")
        self.log(f"Fail: {bad}")

        self.convert_btn.disabled = False
        self.select_btn.disabled = False
        self.clear_btn.disabled = False

        self.selected.clear()

        for r in self.rows:
            r.set_selected(False)


ConverterApp().run()