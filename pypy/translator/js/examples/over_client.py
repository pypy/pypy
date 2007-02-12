
""" Client side of overmind.py
"""

from pypy.translator.js.examples.overmind import exported_methods
from pypy.translator.js.modules import dom

def callback(arg):
    dom.window.location = "http://localhost:%d" % arg

def launch_console():
    exported_methods.launch_console(callback)
