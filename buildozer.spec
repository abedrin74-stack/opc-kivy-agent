[app]
title = OpcMobileAgent
package.name = opcmobileagent
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3,kivy,asyncua

orientation = portrait
fullscreen = 1
android.permissions = INTERNET

# Жестко фиксируем проверенные версии инструментов
android.api = 33
android.minapi = 24
android.ndk = 25b
android.ndk_api = 21
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
