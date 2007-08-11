
""" This file creates and maintains _cache/stdtypes.py, which
keeps information about C type sizes
"""

import py
import os
from pypy.translator.tool.cbuild import build_executable
from pypy.tool.udir import udir
from pypy.tool.autopath import pypydir
from pypy.rlib import rarithmetic
from pypy.rpython.lltypesystem import lltype

def ask_gcc(question, includes=[], add_source="", include_dirs=[],
            compiler_exe=None):
    from py.compat.subprocess import PIPE, Popen
    includes.append('stdio.h')
    includes.append('sys' + os.path.sep + 'types.h')
    include_string = "\n".join(["#include <%s>" % i for i in includes])
    c_source = py.code.Source('''
    // includes
    %s

    %s

    // checking code
    int main(void)
    {
       %s
       return (0);
    }
    ''' % (include_string, add_source, str(question)))
    c_file = udir.join("gcctest.c")
    c_file.write(c_source)

    # always include pypy include dir
    pypypath = py.path.local(pypydir)
    include_dirs = include_dirs[:]
    include_dirs.append(str(pypypath.join('translator', 'c', 'src')))

    c_exec = build_executable([str(c_file)], include_dirs=include_dirs,
                              compiler_exe=compiler_exe)
    pipe = Popen(c_exec, stdout=PIPE)
    pipe.wait()
    return pipe.stdout.read()

def sizeof_c_type(c_typename, **kwds):
    question = 'printf("%%d", sizeof(%s));' % (c_typename,);
    return int(ask_gcc(question, **kwds))

def c_ifdefined(c_def, **kwds):
    question = py.code.Source("""
    #ifdef %s
      printf("0");
    #endif
    """ % (c_def,))
    return ask_gcc(question, **kwds) == '0'

def c_defined_int(c_def, **kwds):
    question = 'printf("%%d", %s);' % (c_def,)
    return int(ask_gcc(question, **kwds))

def create_cache_access_method(acc_func, meth_name):
    def method(self, name, **kwds):
        try:
            return self.cache[name]
        except KeyError:
            res = acc_func(name, **kwds)
            self.cache[name] = res
            self._store_cache()
            return res
    method.func_name = meth_name
    return method

class RffiCache(object):
    """ Class holding all of the c-level caches, eventually loaded from
    the file, like #ifdefs, typesizes, int-level #defines
    """
    def __init__(self, filename):
        self.filename = filename
        self.numbertype_to_rclass = {}
        self.types = {}
        try:
            mod = {}
            exec py.path.local(filename).read() in mod
            self.cache = mod['cache']
            self.type_names = mod['type_names']
            self._build_types()
        except (py.error.ENOENT, KeyError):
            self.cache = {}
            self.type_names = {}

    def _build_types(self):
        for name, (c_name, signed) in self.type_names.items():
            bits = self.cache[c_name]
            inttype = rarithmetic.build_int('r_' + name, signed, bits)
            tp = lltype.build_number(name, inttype)
            self.numbertype_to_rclass[tp] = inttype
            self.types[name] = tp

    def inttype(self, name, c_name, signed, **kwds):
        # XXX sign should be inferred somehow automatically
        try:
            return self.types[name]
        except KeyError:
            bits = sizeof_c_type(c_name, **kwds) * 8
            inttype = rarithmetic.build_int('r_' + name, signed, bits)
            self.cache[c_name] = bits
            self.type_names[name] = (c_name, signed)
            tp = lltype.build_number(name, inttype)
            self.numbertype_to_rclass[tp] = inttype
            self.types[name] = tp
            self._store_cache()
            return tp

    defined = create_cache_access_method(c_ifdefined, 'defined')
    intdefined = create_cache_access_method(c_defined_int, 'intdefined')
    sizeof = create_cache_access_method(sizeof_c_type, 'sizeof')

    # optimal way of caching it, would be to store file on __del__,
    # but since we cannot rely on __del__ having all modules, let's
    # do it after each change :-(
    def _store_cache(self):
        types = 'type_names = ' + repr(self.type_names) + '\n'
        py.path.local(self.filename).write('cache = ' + repr(self.cache)
                                           + '\n' + types)

import pypy
import py
py.path.local(pypy.__file__).new(basename='_cache').ensure(dir=1)
from pypy.tool import autopath
CACHE = py.magic.autopath()/'..'/'..'/'..'/'_cache'/'stdtypes.py'
platform = RffiCache(CACHE)

