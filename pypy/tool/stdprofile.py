#! /usr/bin/env python

import autopath
import hotshot, os
from pypy.objspace.std import StdObjSpace

try:
    os.unlink('profile.log')
except:
    pass

p = hotshot.Profile('profile.log')
p.run('StdObjSpace()')
p.close()

print 'loading...'

import hotshot.stats
p = hotshot.stats.load('profile.log')
p.strip_dirs()
p.sort_stats('time', 'calls')
p.print_stats(20)

