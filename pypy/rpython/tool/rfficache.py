
# XXX This is completely outdated file, kept here only for bootstrapping
#     reasons. If you touch it, try removing it

import py
import os
import distutils
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.tool.udir import udir
from pypy.tool.autopath import pypydir
from pypy.rlib import rarithmetic
from pypy.rpython.lltypesystem import lltype
from pypy.tool.gcc_cache import build_executable_cache

def ask_gcc(question, add_source=""):
    includes = ['stdlib.h', 'sys/types.h']
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
    eci = ExternalCompilationInfo()
    return build_executable_cache([c_file], eci)

def sizeof_c_type(c_typename, **kwds):
    question = 'printf("%%d", sizeof(%s));' % (c_typename,);
    return int(ask_gcc(question, **kwds))

class Platform:
    def __init__(self):
        self.types = {}
        self.numbertype_to_rclass = {}
    
    def inttype(self, name, c_name, signed, **kwds):
        try:
            return self.types[name]
        except KeyError:
            bits = sizeof_c_type(c_name, **kwds) * 8
            inttype = rarithmetic.build_int('r_' + name, signed, bits)
            tp = lltype.build_number(name, inttype)
            self.numbertype_to_rclass[tp] = inttype
            self.types[name] = tp
            return tp

platform = Platform()
