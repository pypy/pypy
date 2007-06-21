
""" This file creates and maintains _cache/rtypes.py, which
keeps information about C type sizes on various platforms
"""

import py
import os
from pypy.translator.tool.cbuild import build_executable
from subprocess import PIPE, Popen
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

def machine_key():
    """ Key unique to machine type, but general enough to share
    it between eg different kernels
    """
    import platform
    return platform.processor(), platform.architecture(), platform.system()

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

def get_type_sizes(filename, platform_key=machine_key(), types=TYPES,
                   compiler_exe=None):
    try:
        mod = {}
        exec py.path.local(filename).read() in mod
        platforms = mod['platforms']
    except (ImportError, py.error.ENOENT):
        platforms = {}
    try:
        result = platforms[platform_key]
        if sorted(result.keys()) != sorted(TYPES):
            # invalidate file
            platforms = {}
            raise KeyError
        return result
    except KeyError:
        value = dict([(i, sizeof_c_type(i, compiler_exe=compiler_exe))
                      for i in types])
        platforms[platform_key] = value
        comment = "# this is automatically generated cache files for c types\n"
        py.path.local(filename).write(comment + 'platforms = ' +
                                      newline_repr(platforms) + "\n")
        return value

from pypy.tool import autopath
CACHE = py.magic.autopath().dirpath().join('typecache.py')
platform = get_type_sizes(CACHE)

