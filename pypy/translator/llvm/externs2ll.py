import os
import sys
import types
import urllib

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

def get_incdirs(c_include_dirs):
    import distutils.sysconfig

    includes = tuple(c_include_dirs) + ("/sw/include",
                distutils.sysconfig.EXEC_PREFIX + "/include", 
                distutils.sysconfig.EXEC_PREFIX + "/include/gc",
                distutils.sysconfig.get_python_inc(),
                get_c_cpath(),
                get_llvm_cpath())

    includestr = ""
    for ii in includes:
        includestr += "-I %s " % ii
    return includestr

# call entrypoint needs to be fastcc
# call boehm finalizers need to be fastcc

def generate_ll(ccode, default_cconv, c_include_dirs, call_funcnames=[]):

    call_funcnames += ['@LLVM_RPython_StartupCode']
    define_funcnames = ['@pypy_malloc',
                        '@pypy_malloc_atomic',
                        '@pypy_gc__collect',
                        '@pypy_register_finalizer']
    declare_funcnames = ['@LLVM_RPython_StartupCode']

    filename = str(udir.join("ccode.c"))
    f = open(filename, "w")
    f.write(ccode)
    f.close()

    plain = filename[:-2]
    includes = get_incdirs(c_include_dirs)
    cmd = "llvm-gcc -emit-llvm -O0 -S %s %s.c -o %s.ll 2>&1" % (
        includes, plain, plain)

    if os.system(cmd) != 0:
        raise Exception("Failed to run '%s'" % cmd)

    llcode = open(plain + '.ll').read()

    # strip lines
    lines = []

    calltag, declaretag, definetag = 'call ', 'declare ', 'define '
    
    for line in llcode.split('\n'):

        # get rid of any of the structs that llvm-gcc introduces to struct types
        line = line.replace("%struct.", "%")

        # strip comments
        comment = line.find(';')
        if comment >= 0:
            line = line[:comment]
        line = line.rstrip()

        # patch calls (upgrade to default_cconv)
        i = line.find(calltag)
        if i >= 0:
            for funcname in call_funcnames:
                if line.find(funcname) >= 0:
                    line = "%scall %s %s" % (line[:i], default_cconv, line[i+len(calltag):])
                    break

        if line[:len(declaretag)] == declaretag:
            xline = line[len(declaretag):] 
            for funcname in declare_funcnames: 
                if xline.find(funcname) != -1:
                    line = "declare %s %s %s" % (internal, default_cconv, xline)
                    break
                    
        if line[:len(definetag)] == definetag:
            xline = line[len(definetag):] 
            internal = ''
            if xline.startswith('internal '):
                internal = 'internal '
                xline = xline.replace('internal ', '')

            for funcname in define_funcnames: 
                if xline.find(funcname) != -1:
                    line = "define %s %s %s" % (internal, default_cconv, xline)
                    break

        lines.append(line)

    lines.append("declare ccc void @abort()")
    return'\n'.join(lines)

def generate_c(db, entrynode, c_includes, c_sources, standalone):
    ccode = []
        
    if standalone:
        ccode.append('#define __ENTRY_POINT__ %s' % entrynode.get_ref()[1:])
        ccode.append('#define ENTRY_POINT_DEFINED 1')

    # include python.h early
    ccode.append('#include <Python.h>')

    # ask gcpolicy for any code needed
    ccode.append('%s' % db.gcpolicy.genextern_code())

    # ask rffi for includes/source
    for c_include in c_includes:
        ccode.append('#include <%s>' % c_include)
        
    ccode.append('')

    for c_source in c_sources:
        ccode.append(c_source) 

    ccode.append('')

    # append our source file
    ccode.append(open(get_module_file('genexterns.c')).read())
    return "\n".join(ccode)
