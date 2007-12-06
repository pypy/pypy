import os
import sys
import types
import urllib

from StringIO import StringIO

from pypy.objspace.flow.model import FunctionGraph
from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem import lltype
from pypy.tool.udir import udir

def get_c_cpath():
    from pypy.translator.c import genc
    return os.path.dirname(genc.__file__)

def get_llvm_cpath():
    return os.path.join(os.path.dirname(__file__), "module")

def get_module_file(name):
    return os.path.join(get_llvm_cpath(), name)

def get_incdirs(eci):
    import distutils.sysconfig

    includes = eci.include_dirs + ("/sw/include",
                distutils.sysconfig.EXEC_PREFIX + "/include", 
                distutils.sysconfig.EXEC_PREFIX + "/include/gc",
                distutils.sysconfig.get_python_inc(),
                get_c_cpath(),
                get_llvm_cpath())

    includestr = ""
    for ii in includes:
        includestr += "-I %s " % ii
    return includestr

def generate_ll(ccode, eci):
    filename = str(udir.join("ccode.c"))
    f = open(filename, "w")
    f.write(ccode)
    f.close()

    plain = filename[:-2]
    includes = get_incdirs(eci)
    cmd = "llvm-gcc -emit-llvm -O0 -S %s %s.c -o %s.ll 2>&1" % (
        includes, plain, plain)

    if os.system(cmd) != 0:
        raise Exception("Failed to run '%s'" % cmd)

    llcode = open(plain + '.ll').read()
 
    # strip lines
    lines = []
    for line in llcode.split('\n'):
        lines.append(line)

    lines.append("declare void @abort()")
    lines.append("declare i32 @write(i32, i8 *, i32)")
    return'\n'.join(lines)

def generate_c(db, entrynode, eci, standalone):
    ccode = []
        
    if standalone:
        ccode.append('#define __ENTRY_POINT__ %s' % entrynode.ref[1:])
        ccode.append('#define ENTRY_POINT_DEFINED 1')

    sio = StringIO()
    eci.write_c_header(sio)
    ccode.extend(sio.getvalue().splitlines())

    # include python.h early
    ccode.append('#include <Python.h>')

    # ask gcpolicy for any code needed
    ccode.append('%s' % db.gcpolicy.genextern_code())

    # append our source file
    ccode.append(open(get_module_file('genexterns.c')).read())
    return "\n".join(ccode)
