#!/usr/bin/env python
from rpython.rlib import jit
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.rsre import rsre_core, rsre_utf8, rpy
from rpython.rlib.rsre.rsre_constants import MAXREPEAT
import os, time

r_code1 = rpy.get_code(ur"<item>\s*<title>(.*?)</title>")
r_code2 = rpy.get_code(ur'[\w\.+-]+@[\w\.-]+\.[\w\.-]+')
r_code3 = rpy.get_code(ur'[\w]+://[^/\s?#]+[^\s?#]+(?:\?[^\s#]*)?(?:#[^\s]*)?')
r_code4 = rpy.get_code(ur'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9])')

driver = jit.JitDriver(greens=["code"], reds="auto", is_recursive=True)

def read(filename):
    fd = os.open(filename, os.O_RDONLY, 0666)
    if fd < 0:
        raise OSError
    end = os.lseek(fd, 0, 2)
    os.lseek(fd, 0, 0)
    data = os.read(fd, intmask(end))
    os.close(fd)
    return data

def search_in_file(codenum, data):
    code = [r_code1, r_code2, r_code3, r_code4][codenum - 1]
    p = 0
    count = 0
    while True:
        driver.jit_merge_point(code=code)
        res = rsre_utf8.utf8search(code, data, p)
        if res is None:
            break
        matchstart, matchstop = res.span(0)
        assert 0 <= matchstart <= matchstop
        p = res.span(0)[1]
        count += 1
    print(count)

# __________  Entry point  __________

def entry_point(argv):
    if len(argv) != 2:
        print "usage: %s <filename>" % (argv[0], )
        return -1
    data = read(argv[1]) # assumed valid utf-8
    for codenum in [1, 2, 3, 4]:
        start = time.time()
        search_in_file(codenum, data)
        stop = time.time()
        print codenum, stop - start
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

# _____ Pure Python equivalent _____

if __name__ == '__main__':
    import re, sys
    entry_point(sys.argv)
    assert 0
    codenum = int(sys.argv[1])
    if codenum < 0:
        sys.argv[1] = -codenum
        entry_point(sys.argv)
    else:
        r = [ 
            ur"<item>\s*<title>(.*?)</title>",
            ur'[\w\.+-]+@[\w\.-]+\.[\w\.-]+',
            ur'[\w]+://[^/\s?#]+[^\s?#]+(?:\?[^\s#]*)?(?:#[^\s]*)?',
            ur'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9])'][int(sys.argv[1]) - 1]
        r = re.compile(r)
        start = time.time()
        f = open(sys.argv[2], 'rb')
        data = f.read()
        f.close()
        for title in r.findall(data):
            print '%s: %s' % (sys.argv[2], title)
        stop = time.time()
        print '%.4fs' % (stop - start,)
