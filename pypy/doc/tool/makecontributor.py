"""

generates a contributor list

"""
import py

try: 
    path = py.std.sys.argv[1]
except IndexError: 
    print "usage: %s PATH" %(py.std.sys.argv[0])
    raise SystemExit, 1

d = {}

for logentry in py.path.svnwc(py.std.sys.argv[1]).log(): 
    a = logentry.author 
    if a in d: 
        d[a] += 1
    else: 
        d[a] = 1

items = d.items()
items.sort(lambda x,y: -cmp(x[1], y[1]))

import uconf # http://codespeak.net/svn/uconf/dist/uconf 

for author, count in items: 
    realname = uconf.system.User(author).realname  # only works on codespeak 
    print "   ", realname 

