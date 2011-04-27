"""
Version numbers exposed by PyPy through the 'sys' module.
"""
import os
import re
from pypy.translator.platform import platform
from pypy.interpreter import gateway

#XXX # the release serial 42 is not in range(16)
CPYTHON_VERSION            = (2, 7, 0, "final", 42)   #XXX # sync patchlevel.h
CPYTHON_API_VERSION        = 1013   #XXX # sync with include/modsupport.h

PYPY_VERSION               = (1, 5, 0, "alpha", 0)    #XXX # sync patchlevel.h

if platform.name == 'msvc':
    COMPILER_INFO = 'MSC v.%d 32 bit' % (platform.version * 10 + 600)
elif platform.cc.startswith('gcc'):
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
from pypy.tool.version import get_repo_version_info

import time as t
gmtime = t.gmtime()
date = t.strftime("%b %d %Y", gmtime)
time = t.strftime("%H:%M:%S", gmtime)
del t

# ____________________________________________________________

app = gateway.applevel('''
"NOT_RPYTHON"
from _structseq import structseqtype, structseqfield
class version_info:
    __metaclass__ = structseqtype

    major        = structseqfield(0, "Major release number")
    minor        = structseqfield(1, "Minor release number")
    micro        = structseqfield(2, "Patch release number")
    releaselevel = structseqfield(3,
                       "'alpha', 'beta', 'candidate', or 'release'")
    serial       = structseqfield(4, "Serial release number")
''')

def get_api_version(space):
    return space.wrap(CPYTHON_API_VERSION)

def get_version_info(space):
    w_version_info = app.wget(space, "version_info")
    return space.call_function(w_version_info, space.wrap(CPYTHON_VERSION))

def get_version(space):
    ver = "%d.%d.%d" % (PYPY_VERSION[0], PYPY_VERSION[1], PYPY_VERSION[2])
    if PYPY_VERSION[3] != "final":
        ver = ver + "-%s%d" %(PYPY_VERSION[3], PYPY_VERSION[4])
    return space.wrap("%d.%d.%d (%s, %s, %s)\n[PyPy %s%s]" % (
        CPYTHON_VERSION[0],
        CPYTHON_VERSION[1],
        CPYTHON_VERSION[2],
        get_repo_version_info()[2],
        date,
        time,
        ver,
        compiler_version()))

def get_winver(space):
    return space.wrap("%d.%d" % (
        CPYTHON_VERSION[0],
        CPYTHON_VERSION[1]))

def get_hexversion(space):
    return space.wrap(tuple2hex(CPYTHON_VERSION))

def get_pypy_version_info(space):
    ver = PYPY_VERSION
    w_version_info = app.wget(space, "version_info")
    return space.call_function(w_version_info, space.wrap(ver))

def get_subversion_info(space):
    return space.wrap(('PyPy', '', ''))

def get_repo_info(space):
    info = get_repo_version_info()
    if info:
        project, repo_tag, repo_version = info
        return space.newtuple([space.wrap(project),
                               space.wrap(repo_tag),
                               space.wrap(repo_version)])
    else:
        return space.w_None

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
