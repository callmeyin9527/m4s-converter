import os
import shutil
import threading
import subprocess
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.uix.textinput import TextInput
from kivy.core.window import Window

# ========== 配置 ==========
SCAN_DIR = "/storage/emulated/0/Download"

from android.storage import app_storage_path

APP_HOME = app_storage_path()
FFMPEG_DIR = os.path.join(APP_HOME, "ffmpeg_libs")
FFMPEG_BIN = os.path.join(FFMPEG_DIR, "ffmpeg")
# =========================

def find_source_ffmpeg():
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "ffmpeg_libs")
    if os.path.isfile(os.path.join(path, "ffmpeg")):
        return path
    return None

def deploy_ffmpeg():
    if os.path.isfile(FFMPEG_BIN):
        try:
            os.chmod(FFMPEG_BIN, 0o755)
            for f in os.listdir(FFMPEG_DIR):
                fp = os.path.join(FFMPEG_DIR, f)
                if os.path.isfile(fp):
                    os.chmod(fp, 0o755)
            return True, ""
        except Exception:
            pass

    src_dir = find_source_ffmpeg()
    if not src_dir:
        return False, (
            "ffmpeg_libs folder not found inside the app.\n"
            "Please ensure the folder is in the same directory as main.py."
        )

    try:
        os.makedirs(FFMPEG_DIR, exist_ok=True)
        for item in os.listdir(src_dir):
            s = os.path.join(src_dir, item)
            d = os.path.join(FFMPEG_DIR, item)
            if os.path.isfile(s):
                shutil.copy2(s, d)
        for f in os.listdir(FFMPEG_DIR):
            fp = os.path.join(FFMPEG_DIR, f)
            if os.path.isfile(fp):
                os.chmod(fp, 0o755)
        return True, ""
    except Exception as e:
        return False, str(e)

class FileRow(BoxLayout):
    def __init__(self, full_path, filename, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=100, padding=(15,0))
        self.full_path = full_path
        self.selected = False

        # 文件名 超大字体
        self.label = Label(
            text=filename,
            halign='left',
            valign='middle',
            size_hint_x=0.5,
            color=(1, 1, 1, 1),
            font_size=24
        )
        self.label.bind(size=self.label.setter('text_size'))

        # Choose 巨型按钮 + 超大字
        self.choose_btn = Button(
            text='Choose',
            size_hint_x=0.5,
            font_size=24,
            background_color=(0.1, 0.6, 0.2, 1)
        )
        self.add_widget(self.label)
        self.add_widget(self.choose_btn)

    def toggle_select(self):
        self.selected = not self.selected
        if self.selected:
            self.choose_btn.background_color = (0.2, 0.4, 0.2, 0.5)
            self.label.color = (1, 0.9, 0.2, 1)
        else:
            self.choose_btn.background_color = (0.1, 0.6, 0.2, 1)
            self.label.color = (1, 1, 1, 1)

class ConverterApp(App):
    def build(self):
        Window.clearcolor = (0.12, 0.13, 0.16, 1)
        self.title = "M4S to MP3"
        self.selected_list = []
        self.file_rows = []

        ok, err = deploy_ffmpeg()
        if not ok:
            root = BoxLayout(orientation='vertical', padding=20)
            root.add_widget(Label(text=f"Error:\n{err}", halign='center', color=(1, 0.3, 0.3, 1), font_size=22))
            return root

        os.environ["LD_LIBRARY_PATH"] = FFMPEG_DIR

        # 主布局 宽松排版 不挤压
        main = BoxLayout(orientation='vertical', padding=20, spacing=18)

        # 顶部超级大标题
        title_label = Label(
            text="M4SToMP3",
            size_hint_y=None,
            height=90,
            bold=True,
            font_size='38sp',
            color=(1,1,1,1)
        )
        main.add_widget(title_label)

        # 状态文字 超大号
        self.status = Label(
            text="Scanning...",
            size_hint_y=None,
            height=45,
            color=(0.8,0.8,0.8,1),
            font_size=22
        )
        main.add_widget(self.status)

        # 文件列表 保留足够高度 不压缩
        scroll = ScrollView(size_hint_y=0.48)
        self.file_container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=15)
        self.file_container.bind(minimum_height=self.file_container.setter('height'))
        scroll.add_widget(self.file_container)
        main.add_widget(scroll)

        # 底部控制栏 超高+大按钮
        controls = BoxLayout(orientation='horizontal', size_hint_y=None, height=90, spacing=18)
        controls.add_widget(Label(text='Quality:', size_hint_x=0.15, color=(1,1,1,1), font_size=22))
        
        self.bitrate_spinner = Spinner(
            text='192k',
            values=['128k','160k','192k','256k','320k'],
            size_hint_x=0.35,
            halign='center',
            font_size=22
        )
        controls.add_widget(self.bitrate_spinner)

        # Change 巨型红色按钮
        self.change_btn = Button(
            text='Change',
            size_hint_x=0.5,
            background_color=(0.7, 0.1, 0.1, 1),
            font_size=26
        )
        self.change_btn.bind(on_press=lambda x: self.start_convert())
        controls.add_widget(self.change_btn)
        main.add_widget(controls)

        # 日志区域 字体放大三倍
        self.log_view = TextInput(
            text='',
            readonly=True,
            size_hint_y=0.22,
            font_size=20,
            hint_text='Logs will appear here...',
            background_color=(0.15,0.15,0.2,1),
            foreground_color=(1,1,1,1)
        )
        main.add_widget(self.log_view)

        self.scan_files()
        return main

    def log(self, msg):
        self.log_view.text = msg

    def scan_files(self):
        self.file_container.clear_widgets()
        self.file_rows.clear()
        self.selected_list.clear()
        Clock.schedule_once(lambda dt: self._do_scan(), 0)

    def _do_scan(self):
        files = []
        if os.path.isdir(SCAN_DIR):
            for f in sorted(os.listdir(SCAN_DIR)):
                if f.lower().endswith('.m4s'):
                    full = os.path.join(SCAN_DIR, f)
                    if os.path.isfile(full):
                        files.append((f, full))
        if files:
            for fname, fpath in files:
                row = FileRow(fpath, fname)
                row.choose_btn.bind(on_press=lambda x, r=row: self.toggle_file(r))
                self.file_container.add_widget(row)
                self.file_rows.append(row)
            self.status.text = f"Found {len(files)} file(s)"
            self.log(f"Found {len(files)} m4s file(s). Tap multiple Choose for batch select.")
        else:
            self.status.text = "No .m4s files found"
            self.log("No .m4s file found in Download.")

    def toggle_file(self, row):
        row.toggle_select()
        if row.selected:
            self.selected_list.append(row.full_path)
        else:
            if row.full_path in self.selected_list:
                self.selected_list.remove(row.full_path)
        self.status.text = f"Selected {len(self.selected_list)} file(s)"

    def start_convert(self):
        if not self.selected_list:
            self.log("Error: Please select at least one file.")
            return
        self.change_btn.disabled = True
        self.status.text = f"Batch converting {len(self.selected_list)} files..."
        self.log(f"Start batch conversion, total: {len(self.selected_list)}")
        threading.Thread(target=self.batch_convert, daemon=True).start()

    def batch_convert(self):
        success = 0
        fail = 0
        bitrate = self.bitrate_spinner.text
        total = len(self.selected_list)

        for idx, in_file in enumerate(self.selected_list):
            out_file = in_file.rsplit(".", 1)[0] + ".mp3"
            current_num = idx + 1
            Clock.schedule_once(lambda dt, n=current_num, t=total:
                setattr(self.status, 'text', f"Converting {n}/{t}"), 0)

            cmd = [FFMPEG_BIN, "-i", in_file, "-vn", "-acodec", "libmp3lame", "-ab", bitrate, "-y", out_file]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode == 0 and os.path.exists(out_file):
                    success += 1
                else:
                    fail += 1
            except Exception:
                fail += 1

        msg = f"Batch Complete\nSuccess: {success} | Fail: {fail}"
        Clock.schedule_once(lambda dt, m=msg: self.finish_batch(m), 0)

    def finish_batch(self, msg):
        self.log(msg)
        self.status.text = "Batch conversion finished"
        self.change_btn.disabled = False
        self.selected_list.clear()
        for row in self.file_rows:
    row.selected = True
    row.toggle_select()

if __name__ == "__main__":
    ConverterApp().run()
