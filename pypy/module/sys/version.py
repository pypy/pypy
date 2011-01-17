"""
Version numbers exposed by PyPy through the 'sys' module.
"""
import os
import re
from pypy.translator.platform import platform

#XXX # the release serial 42 is not in range(16)
CPYTHON_VERSION            = (2, 7, 0, "final", 42)   #XXX # sync patchlevel.h
CPYTHON_API_VERSION        = 1013   #XXX # sync with include/modsupport.h

PYPY_VERSION               = (1, 4, 1, "beta", 0)    #XXX # sync patchlevel.h

if platform.name == 'msvc':
    COMPILER_INFO = 'MSC v.%d 32 bit' % (platform.version * 10 + 600)
elif platform.cc == 'gcc':
    out = platform.execute(platform.cc, '--version').out
    match = re.search(' (\d+\.\d+(\.\d+)*)', out)
    if match:
        COMPILER_INFO = "GCC " + match.group(1)
    else:
        COMPILER_INFO = "GCC"
else:
    COMPILER_INFO = ""


import pypy
pypydir = os.path.dirname(os.path.abspath(pypy.__file__))
del pypy
from pypy.tool.version import get_mercurial_info

import time as t
gmtime = t.gmtime()
date = t.strftime("%b %d %Y", gmtime)
time = t.strftime("%H:%M:%S", gmtime)
del t

# ____________________________________________________________

def get_api_version(space):
    return space.wrap(CPYTHON_API_VERSION)

def get_version_info(space):
    return space.wrap(CPYTHON_VERSION)

def get_version(space):
    return space.wrap("%d.%d.%d (%s, %s, %s)\n[PyPy %d.%d.%d%s]" % (
        CPYTHON_VERSION[0],
        CPYTHON_VERSION[1],
        CPYTHON_VERSION[2],
        hg_universal_id(),
        date,
        time,
        PYPY_VERSION[0],
        PYPY_VERSION[1],
        PYPY_VERSION[2],
        compiler_version()))

def get_winver(space):
    return space.wrap("%d.%d" % (
        CPYTHON_VERSION[0],
        CPYTHON_VERSION[1]))

def get_hexversion(space):
    return space.wrap(tuple2hex(CPYTHON_VERSION))

def get_pypy_version_info(space):
    ver = PYPY_VERSION
    #ver = ver[:-1] + (svn_revision(),)
    return space.wrap(ver)

def get_subversion_info(space):
    return space.wrap(('PyPy', '', ''))


def wrap_mercurial_info(space):
    info = get_mercurial_info()
    if info:
        project, hgtag, hgid = info
        return space.newtuple([space.wrap(project),
                               space.wrap(hgtag),
                               space.wrap(hgid)])
    else:
        return space.w_None

def hg_universal_id():
    info = get_mercurial_info()
    if info:
        return info[2]
    else:
        return '?'


def tuple2hex(ver):
    d = {'alpha':     0xA,
         'beta':      0xB,
         'candidate': 0xC,
         'final':     0xF,
         }
    subver = ver[4]
    if not (0 <= subver <= 9):
        subver = 0
    return (ver[0] << 24   |
            ver[1] << 16   |
            ver[2] << 8    |
            d[ver[3]] << 4 |
            subver)

def compiler_version():
    if not COMPILER_INFO:
        return ""
    return " with %s" % (COMPILER_INFO,)
