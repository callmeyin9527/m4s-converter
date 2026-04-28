[app]
title = M4SToMP3
package.name = m4stomp3
package.domain = org.m4s.convert
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,txt,so
version = 1.0

requirements = python3,kivy
python.entry_point = main.py

android.add_assets = ffmpeg_libs
android.allow_external_libs = True

android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE
android.request_legacy_storage = True

android.ndk = 25b
android.api = 33
android.minapi = 24
android.sdk = 24

android.enable_androidx = False
android.use_android_ndk = True

p4a.dir = ~/.local/share/python-for-android
p4a.bootstrap = sdl2

orientation = portrait
log_level = 2
buildozer.debug = True
