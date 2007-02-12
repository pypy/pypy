
""" Client side of overmind.py
"""

from pypy.translator.js.examples.overmind import exported_methods
from pypy.translator.js.modules import dom

def callback(port):
    hname = dom.window.location.hostname
    dom.window.location.assign("http://%s:%d" % (hname, port))

def launch_console():
    exported_methods.launch_console(callback)
