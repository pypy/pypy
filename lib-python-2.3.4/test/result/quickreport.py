#! /usr/bin/env python

import sys; sys.path.insert(0, '../../..')
import py, re

mydir = py.magic.autopath().dirpath()

r_end = re.compile(r"""(.+)\s*========================== closed ==========================
execution time: (.+) seconds
exit status: (.+)
$""")

r_timeout = re.compile(r"""==========================timeout==========================
""")

r_importerror = re.compile(r"ImportError: (\w+)")

# Linux list below.  May need to add a few ones for Windows...
IGNORE_MODULES = """
    array          datetime       md5          regex     _testcapi
    audioop        dbm            mmap         resource  time
    binascii       dl             mpz          rgbimg    timing
    _bsddb         fcntl          nis          rotor     _tkinter
    bz2            gdbm           operator     select    unicodedata
    cmath          grp            ossaudiodev  sha       _weakref
    cPickle        _hotshot       parser       _socket   xreadlines
    crypt          imageop        pcre         _ssl      zlib
    cStringIO      itertools      pwd          strop
    _csv           linuxaudiodev  pyexpat      struct
    _curses_panel  _locale        _random      syslog
    _curses        math           readline     termios

    thread

""".split()


class Result:
    pts = '?'
    name = '?'
    exit_status = '?'
    execution_time = '?'
    timeout = False
    finalline = ''
    
    def read(self, fn):
        self.name = fn.purebasename
        data = fn.read(mode='r')
        self.timeout = bool(r_timeout.search(data))
        match = r_end.search(data)
        assert match
        self.execution_time = float(match.group(2))
        self.exit_status = match.group(3)
        if self.exit_status == '0':
            self.pts = 'Ok'
        elif not self.timeout:
            self.finalline = match.group(1)
            self.pts = 'ERR'
            match1 = r_importerror.match(self.finalline)
            if match1:
                module = match1.group(1)
                if module in IGNORE_MODULES:
                    self.pts = ''   # doesn't count in our total
            elif self.finalline.startswith('TestSkipped: '):
                self.pts = ''
        else:
            self.finalline = 'TIME OUT'
            self.pts = 'T/O'

    def __str__(self):
        return '%-3s %-17s %3s  %5s  %s' % (
            self.pts,
            self.name,
            self.exit_status,
            str(self.execution_time)[:5],
            self.finalline)

header = Result()
header.pts = 'res'
header.name = 'name'
header.exit_status = 'err'
header.execution_time = 'time'
header.finalline = '  last output line'
print
print header
print


files = mydir.listdir("*.txt")
files.sort(lambda x,y: cmp(str(x).lower(), str(y).lower()))
for fn in files:
    result = Result()
    try:
        result.read(fn)
    except AssertionError:
        pass
    print result

print
