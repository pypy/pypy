#
# Script to build the PyPy Installer
#
import sys
import subprocess


candle = "candle.exe"
pypywxs = "pypy.wxs"
light = "light.exe"
wixobj = "pypy.wixobj"
path =  "pypy3-v6.0.0-win32"


build = subprocess.Popen([candle, pypywxs])
build.wait()

if build.returncode != 0:
    sys.exit("Failed to run candle")

build = subprocess.Popen([light ,"-ext", "WixUIExtension" ,"-b" , path , wixobj])
build.wait()

if build.returncode != 0:
    sys.exit("Failed to run light")
