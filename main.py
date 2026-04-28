import os
import shutil
import threading
import subprocess
import zipfile

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.uix.textinput import TextInput
from kivy.core.window import Window

from android.storage import app_storage_path

# ==========================
SCAN_DIR = "/storage/emulated/0/Download"

APP_HOME = app_storage_path()
FFMPEG_DIR = os.path.join(APP_HOME, "ffmpeg_libs")
FFMPEG_BIN = os.path.join(FFMPEG_DIR, "ffmpeg")

ZIP_PATH = os.path.join(os.path.dirname(__file__), "ffmpeg_libs.zip")
# ==========================


def unzip_ffmpeg():
    if not os.path.exists(FFMPEG_DIR):
        try:
            with zipfile.ZipFile(ZIP_PATH, "r") as zip_ref:
                zip_ref.extractall(APP_HOME)
        except Exception as e:
            return False, str(e)
    return True, ""


def find_source_ffmpeg():
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "ffmpeg_libs")
    if os.path.isfile(os.path.join(path, "ffmpeg")):
        return path
    return None


def deploy_ffmpeg():
    if os.path.isfile(FFMPEG_BIN):
        os.chmod(FFMPEG_BIN, 0o755)
        return True, ""

    src = find_source_ffmpeg()
    if not src:
        return False, "ffmpeg not found"

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


class FileRow(BoxLayout):
    def __init__(self, full_path, filename):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            height=90,
            spacing=10
        )

        self.full_path = full_path
        self.selected = False

        self.label = Label(
            text=filename,
            font_size=22,
            size_hint_x=0.65
        )

        self.btn = Button(
            text="Choose",
            font_size=22,
            size_hint_x=0.35,
            background_color=(0.1, 0.6, 0.2, 1)
        )

        self.add_widget(self.label)
        self.add_widget(self.btn)

    def toggle(self):
        self.selected = not self.selected

        if self.selected:
            self.btn.text = "Selected"
            self.btn.background_color = (0.8, 0.2, 0.2, 1)
        else:
            self.btn.text = "Choose"
            self.btn.background_color = (0.1, 0.6, 0.2, 1)


class ConverterApp(App):

    def build(self):

        ok, err = unzip_ffmpeg()
        if not ok:
            return Label(text=err)

        ok, err = deploy_ffmpeg()
        if not ok:
            return Label(text=err)

        os.environ["LD_LIBRARY_PATH"] = FFMPEG_DIR

        Window.clearcolor = (0.12, 0.13, 0.16, 1)

        self.rows = []
        self.selected = []

        root = BoxLayout(
            orientation="vertical",
            padding=15,
            spacing=12
        )

        root.add_widget(Label(
            text="M4S To MP3",
            font_size=34,
            size_hint_y=None,
            height=70
        ))

        self.status = Label(
            text="Scanning...",
            font_size=20,
            size_hint_y=None,
            height=45
        )
        root.add_widget(self.status)

        scroll = ScrollView(size_hint_y=0.5)

        self.box = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=10
        )
        self.box.bind(minimum_height=self.box.setter("height"))

        scroll.add_widget(self.box)
        root.add_widget(scroll)

        bottom = BoxLayout(
            size_hint_y=None,
            height=80,
            spacing=10
        )

        self.spinner = Spinner(
            text="192k",
            values=("128k", "160k", "192k", "256k", "320k"),
            font_size=22
        )

        self.btn = Button(
            text="Convert",
            font_size=24,
            background_color=(0.7, 0.1, 0.1, 1)
        )
        self.btn.bind(on_press=lambda x: self.start())

        bottom.add_widget(self.spinner)
        bottom.add_widget(self.btn)

        root.add_widget(bottom)

        self.logbox = TextInput(
            readonly=True,
            font_size=18,
            size_hint_y=0.25
        )
        root.add_widget(self.logbox)

        self.scan()

        return root

    def log(self, txt):
        self.logbox.text = txt

    def scan(self):
        self.box.clear_widgets()
        self.rows.clear()

        if not os.path.isdir(SCAN_DIR):
            self.status.text = "Download folder missing"
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

            row = FileRow(path, name)
            row.btn.bind(on_press=lambda x, r=row: self.pick(r))

            self.rows.append(row)
            self.box.add_widget(row)

        self.status.text = f"Found {len(files)} file(s)"

    def pick(self, row):
        row.toggle()

        if row.selected:
            self.selected.append(row.full_path)
        else:
            if row.full_path in self.selected:
                self.selected.remove(row.full_path)

        self.status.text = f"Selected {len(self.selected)}"

    def start(self):
        if not self.selected:
            self.log("Please choose file.")
            return

        self.btn.disabled = True
        threading.Thread(target=self.work).start()

    def work(self):
        ok = 0
        bad = 0

        bitrate = self.spinner.text
        total = len(self.selected)

        for i, src in enumerate(self.selected):

            out = src.rsplit(".", 1)[0] + ".mp3"

            Clock.schedule_once(
                lambda dt, n=i + 1:
                setattr(self.status, "text", f"Converting {n}/{total}")
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
                r = subprocess.run(cmd)

                if r.returncode == 0:
                    ok += 1
                else:
                    bad += 1

            except:
                bad += 1

        Clock.schedule_once(
            lambda dt: self.finish(ok, bad)
        )

    def finish(self, ok, bad):
        self.status.text = "Finished"
        self.log(f"Success:{ok}  Fail:{bad}")

        self.btn.disabled = False

        self.selected.clear()

        for r in self.rows:
            if r.selected:
                r.toggle()


ConverterApp().run()