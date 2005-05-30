import autopath
import os
from pypy.translator.c.node import PyObjectNode


def gen_source(database, modulename, targetdir, defines={}):
    filename = os.path.join(targetdir, modulename + '.c')
    f = open(filename, 'w')

    #
    # Header
    #
    for key, value in defines.items():
        print >> f, '#define %s %s' % (key, value)
    print >> f, '#include "g_include.h"'

    #
    # All declarations
    #
    print >> f
    print >> f, '/***********************************************************/'
    print >> f, '/***  Structure definitions                              ***/'
    print >> f
    for node in database.structdeflist:
        for line in node.definition():
            print >> f, line
    print >> f
    print >> f, '/***********************************************************/'
    print >> f, '/***  Forward declarations                               ***/'
    print >> f
    for node in database.globalcontainers():
        for line in node.forward_declaration():
            print >> f, line

    #
    # Implementation of functions and global structures and arrays
    #
    print >> f
    print >> f, '/***********************************************************/'
    print >> f, '/***  Implementations                                    ***/'
    for node in database.globalcontainers():
        print >> f
        for line in node.implementation():
            print >> f, line

    #
    # PyObject support (strange) code
    #
    pyobjmaker = database.pyobjmaker
    print >> f
    print >> f, '/***********************************************************/'
    print >> f, '/***  Table of global PyObjects                          ***/'
    print >> f
    print >> f, 'static globalobjectdef_t globalobjectdefs[] = {'
    for node in database.globalcontainers():
        if isinstance(node, PyObjectNode):
            name = node.name
            if name not in pyobjmaker.wrappers:
                print >> f, '\t{&%s, "%s"},' % (name, name)
    print >> f, '\t{ NULL }\t/* Sentinel */'
    print >> f, '};'
    print >> f
    print >> f, '/***********************************************************/'
    print >> f, '/***  Table of functions                                 ***/'
    print >> f
    print >> f, 'static globalfunctiondef_t globalfunctiondefs[] = {'
    wrappers = pyobjmaker.wrappers.items()
    wrappers.sort()
    for globalobject_name, (base_name, wrapper_name) in wrappers:
        print >> f, ('\t{&%s, {"%s", (PyCFunction)%s, '
                     'METH_VARARGS|METH_KEYWORDS}},' % (
            globalobject_name,
            base_name,
            wrapper_name))
    print >> f, '\t{ NULL }\t/* Sentinel */'
    print >> f, '};'
    print >> f
    print >> f, '/***********************************************************/'
    print >> f, '/***  Frozen Python bytecode: the initialization code    ***/'
    print >> f
    print >> f, 'static char *frozen_initcode[] = {"\\'
    bytecode, originalsource = database.pyobjmaker.getfrozenbytecode()
    g = open(os.path.join(targetdir, 'frozen.py'), 'w')
    g.write(originalsource)
    g.close()
    def char_repr(c):
        if c in '\\"': return '\\' + c
        if ' ' <= c < '\x7F': return c
        return '\\%03o' % ord(c)
    for i in range(0, len(bytecode), 32):
        print >> f, ''.join([char_repr(c) for c in bytecode[i:i+32]])+'\\'
        if (i+32) % 1024 == 0:
            print >> f, '", "\\'
    print >> f, '"};'
    print >> f, "#define FROZEN_INITCODE_SIZE %d" % len(bytecode)
    print >> f

    #
    # Module initialization function
    #
    print >> f, '/***********************************************************/'
    print >> f, '/***  Module initialization function                     ***/'
    print >> f
    print >> f, 'MODULE_INITFUNC(%s)' % modulename
    print >> f, '{'
    print >> f, '\tSETUP_MODULE(%s)' % modulename
    #print >> f, '\tPyModule_AddObject(m, "%(entrypointname)s", %(entrypoint)s);'
    print >> f, '}'
    f.close()

    #
    # Generate a setup.py while we're at it
    #
    pypy_include_dir = autopath.this_dir
    f = open(os.path.join(targetdir, 'setup.py'), 'w')
    f.write(SETUP_PY % locals())
    f.close()


SETUP_PY = '''
from distutils.core import setup
from distutils.extension import Extension
from distutils.ccompiler import get_default_compiler

PYPY_INCLUDE_DIR = %(pypy_include_dir)r

extra_compile_args = []
if get_default_compiler() == "unix":
    extra_compile_args.extend(["-Wno-unused-label",
                               "-Wno-unused-variable"])

setup(name="%(modulename)s",
      ext_modules = [Extension(name = "%(modulename)s",
                            sources = ["%(modulename)s.c"],
                 extra_compile_args = extra_compile_args,
                       include_dirs = [PYPY_INCLUDE_DIR])])
'''
