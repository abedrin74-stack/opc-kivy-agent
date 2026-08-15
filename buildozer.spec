[app]
title = OpcMobileAgent
package.name = opcmobileagent
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3==3.11.0,hostpython3==3.11.0,kivy==2.3.0,asyncua==1.1.5
orientation = portrait
fullscreen = 1
android.permissions = INTERNET
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
