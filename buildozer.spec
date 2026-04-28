[app]

title = M4SToMP3
package.name = m4stomp3
package.domain = org.m4s.convert

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,txt,so,zip

version = 1.0

requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 24
android.ndk = 25b

android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE

android.add_assets = ffmpeg_libs.zip

p4a.bootstrap = sdl2

log_level = 2
buildozer.warn_on_root = 0