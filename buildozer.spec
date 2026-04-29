[app]

title = M4S TO MP3
package.name = m4stomp3
package.domain = org.gg

source.dir = .
source.include_exts = py,png,jpg,kv,so,zip
source.include_patterns = ffmpeg_libs/*,ffmpeg_libs.zip

version = 1.0

requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE

android.api = 33
android.minapi = 24
android.sdk = 33
android.ndk = 25b

android.arch = arm64-v8a

android.allow_backup = True
android.accept_sdk_license = True

# icon.filename = icon.png


[buildozer]

log_level = 2
warn_on_root = 1