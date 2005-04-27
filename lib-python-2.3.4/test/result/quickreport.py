#! /usr/bin/env python

"""
A quick reporting tool, showing the exit status and last line of each test.

In the first column, quickreport attempts to categorize the test result:

    Ok    passed.
    ERR   failed.
          (blank) ImportError, one of the known-missing modules listed below.
    ?     parse error, maybe the test is currently running.
    T/O   time out.

When called with arguments, quickreport prints the name of the tests that
match them.  The first argument is the category (ok, err, t/o) and the
optional following arguments are searched for in the last column of the
table.
"""

import sys; sys.path.insert(0, '../../..')
import py, re

mydir = py.magic.autopath().dirpath()

r_end = re.compile(r"""(.+)\s*========================== closed ==========================
execution time: (.+) seconds
exit status: (.+)
$""")

r_timeout = re.compile(r"""==========================timeout==========================
""")

r_importerror = re.compile(r"ImportError: (.+)")

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
    cStringIO      itertools      pwd          strop     _winreg
    _csv           linuxaudiodev  pyexpat      struct    winsound
    _curses_panel  _locale        _random      syslog    aetools
    _curses        math           readline     termios   sunaudiodev

    bsddb185

    thread
    signal

""".split()

IGNORE_MODULES.extend("aepack".split())   # Mac ext stuff
IGNORE_MODULES.extend("al cd cl".split()) # old SGI IRIX extensions


IGNORE_MODULES.append("no XML parsers available")
IGNORE_MODULES.append("test_support must be imported from the test package")

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
        if (self.exit_status == '0' and
            not match.group(1).lower().startswith('fail')):
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
            elif self.finalline == 'skipping curses':
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


def allresults():
    files = mydir.listdir("*.txt")
    files.sort(lambda x,y: cmp(str(x).lower(), str(y).lower()))
    for fn in files:
        result = Result()
        try:
            result.read(fn)
        except AssertionError:
            pass
        yield result


def report_table():
    header = Result()
    header.pts = 'res'
    header.name = 'name'
    header.exit_status = 'err'
    header.execution_time = 'time'
    header.finalline = '  last output line'
    print
    print header
    print
    for result in allresults():
        print result
    print


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        report_table()
    else:
        match_pts = sys.argv[1].upper()
        match_finalline = '\s+'.join([re.escape(s) for s in sys.argv[2:]])
        r_match_finalline = re.compile(match_finalline)
        for result in allresults():
            if result.pts.upper() == match_pts:
                if r_match_finalline.search(result.finalline):
                    print result.name
