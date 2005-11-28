import py

release_URL = 'http://codespeak.net/svn/pypy/release/'
releases = [r[:-2] for r in py.std.os.popen('svn list ' + release_URL).readlines() if 'x' not in r]

f = file('release_dates.txt', 'w')
print >> f, 'date, release'
for release in releases:
    for s in py.std.os.popen('svn info ' + release_URL + release).readlines():
        if s.startswith('Last Changed Date'):
            date = s.split()[3]
            print >> f, date, ',', release
            break
f.close()
