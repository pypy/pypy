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

# Authors that don't want to be listed
excluded = set("anna gintas ignas".split())
cutoff = 5 # cutoff for authors in the LICENSE file
mark = False
for author, count in items: 
    user = uconf.system.User(author)
    try:
        realname = user.realname.strip()
    except KeyError:
        realname = author
    if not mark and count < cutoff:
        mark = True
        print '-'*60
    print "   ", realname
    #print count, "   ", author 
