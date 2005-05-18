"""
    Standard Library usage demo.
    Uses urllib and htmllib to download and parse a web page.

    The purpose of this demo is to remind and show that almost all
    pure-Python modules of the Standard Library work just fine.
"""

url = 'http://www.python.org/'
html = 'python.html'
import urllib
content = urllib.urlopen(url).read()
file(html, 'w').write(content)
import htmllib
htmllib.test([html])
import os
os.remove(html)
