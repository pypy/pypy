url = 'http://www.python.org/'
html = 'python.html'
import urllib
content = urllib.urlopen(url).read()
file(html, 'w').write(content)
import htmllib
htmllib.test([html])
import os
os.remove(html)
