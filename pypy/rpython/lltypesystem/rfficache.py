
""" This file creates and maintains _cache/stdtypes.py, which
keeps information about C type sizes
"""

import py
import os
from pypy.translator.tool.cbuild import build_executable
from py.compat.subprocess import PIPE, Popen
from pypy.tool.udir import udir

def sizeof_c_type(c_typename, includes={}, compiler_exe=None):
    includes['stdio.h'] = True
    includes['sys' + os.path.sep + 'types.h'] = True
    include_string = "\n".join(["#include <%s>" % i for i in includes.keys()])
    c_source = py.code.Source('''
    // includes
    %s

    // checking code
    int main(void)
    {
       printf("%%d\\n", sizeof(%s));
       return (0);
    }
    ''' % (include_string, c_typename))
    c_file = udir.join("typetest.c")
    c_file.write(c_source)

    c_exec = build_executable([str(c_file)], compiler_exe=compiler_exe)
    pipe = Popen(c_exec, stdout=PIPE)
    pipe.wait()
    return int(pipe.stdout.read()) * 8

# XXX add float types as well here

TYPES = []
for _name in 'char short int long'.split():
    for name in (_name, 'unsigned ' + _name):
        TYPES.append(name)
TYPES += ['long long', 'unsigned long long', 'size_t']
if os.name != 'nt':
    TYPES.append('mode_t')

def newline_repr(d):
    assert isinstance(d, dict)
    return "{\n%s,\n}" % ",\n".join(["%r:%r" % (k, v) for k, v in d.items()])

def get_type_sizes(filename, compiler_exe=None):
    try:
        mod = {}
        exec py.path.local(filename).read() in mod
        types = mod['types']
    except (ImportError, py.error.ENOENT):
        types = {}
    try:
        if py.builtin.sorted(types.keys()) != py.builtin.sorted(TYPES):
            # invalidate file
            types = {}
            raise KeyError
        return types
    except KeyError:
        types = dict([(i, sizeof_c_type(i, compiler_exe=compiler_exe))
                      for i in TYPES])
        py.path.local(filename).write('types = ' +
                                      repr(types) + "\n")
        return types

import pypy
import py
py.path.local(pypy.__file__).new(basename='_cache').ensure(dir=1)
from pypy.tool import autopath
CACHE = py.magic.autopath()/'..'/'..'/'..'/'_cache'/'stdtypes.py'
platform = get_type_sizes(CACHE)

