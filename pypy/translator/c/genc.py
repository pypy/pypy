import autopath
import os, py
from pypy.translator.c.node import PyObjectNode
from pypy.translator.c.database import LowLevelDatabase
from pypy.translator.c.extfunc import pre_include_code_lines
from pypy.translator.gensupp import uniquemodulename
from pypy.translator.tool.buildpyxmodule import make_module_from_c
from pypy.rpython.lltype import pyobjectptr
from pypy.tool.udir import udir


def translator2database(translator):
    pf = pyobjectptr(translator.entrypoint)
    db = LowLevelDatabase(translator)
    db.get(pf)
    db.complete()
    return db, pf


def genc(translator, targetdir=None, modulename=None, compile=True,
                                                      symtable=True):
    """Generate C code starting at the translator's entry point.
    The files are written to the targetdir if specified.
    If 'compile' is True, compile and return the new module.
    If 'compile' is False, just return the name of the main '.c' file.
    """
    db, pf = translator2database(translator)

    if modulename is None:
        modulename = uniquemodulename('testing')
    if targetdir is None:
        targetdir = udir.join(modulename)
    elif isinstance(targetdir, str):
        targetdir = py.path.local(targetdir)
    targetdir.ensure(dir=1)
    if symtable:
        from pypy.translator.c.symboltable import SymbolTable
        symboltable = SymbolTable()
    else:
        symboltable = None
    cfile = gen_source(db, modulename, targetdir,
                       # defines={'COUNT_OP_MALLOCS': 1},
                       exports = {translator.entrypoint.func_name: pf},
                       symboltable = symboltable)
    if not compile:
        return cfile
    m = make_module_from_c(cfile, include_dirs = [autopath.this_dir])
    symboltable.attach(m)   # hopefully temporary hack
    return m


# ____________________________________________________________

def gen_readable_parts_of_main_c_file(f, database, preimplementationlines=[]):
    #
    # All declarations
    #
    print >> f
    print >> f, '/***********************************************************/'
    print >> f, '/***  Structure definitions                              ***/'
    print >> f
    for node in database.structdeflist:
        for line in node.definition(phase=1):
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
    print >> f
    for line in preimplementationlines:
        print >> f, line
    print >> f, '#include "src/g_include.h"'
    print >> f
    blank = False
    for node in database.structdeflist:
        for line in node.definition(phase=2):
            print >> f, line
        blank = True
    for node in database.globalcontainers():
        if blank:
            print >> f
            blank = False
        for line in node.implementation():
            print >> f, line
            blank = True


def gen_source(database, modulename, targetdir, defines={}, exports={},
                                                symboltable=None):
    if isinstance(targetdir, str):
        targetdir = py.path.local(targetdir)
    filename = targetdir.join(modulename + '.c')
    f = filename.open('w')

    #
    # Header
    #
    for key, value in defines.items():
        print >> f, '#define %s %s' % (key, value)
    print >> f, '#include "Python.h"'
    includes = {}
    for node in database.globalcontainers():
        for include in node.includes:
            includes[include] = True
    includes = includes.keys()
    includes.sort()
    for include in includes:
        print >> f, '#include <%s>' % (include,)

    if database.translator is None or database.translator.rtyper is None:
        preimplementationlines = []
    else:
        preimplementationlines = list(
            pre_include_code_lines(database, database.translator.rtyper))

    #
    # 1) All declarations
    # 2) Implementation of functions and global structures and arrays
    #
    gen_readable_parts_of_main_c_file(f, database, preimplementationlines)

    #
    # Debugging info
    #
    if symboltable:
        print >> f
        print >> f, '/*******************************************************/'
        print >> f, '/***  Debugging info                                 ***/'
        print >> f
        print >> f, 'static int debuginfo_offsets[] = {'
        for node in database.structdeflist:
            for expr in symboltable.generate_type_info(database, node):
                print >> f, '\t%s,' % expr
        print >> f, '\t0 };'
        print >> f, 'static void *debuginfo_globals[] = {'
        for node in database.globalcontainers():
            if not isinstance(node, PyObjectNode):
                result = symboltable.generate_global_info(database, node)
                print >> f, '\t%s,' % (result,)
        print >> f, '\tNULL };'
        print >> f, '#include "src/debuginfo.h"'

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
            for target in node.where_to_copy_me:
                print >> f, '\t{%s, "%s"},' % (target, node.name)
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
        print >> f, ('\t{&%s, "%s", {"%s", (PyCFunction)%s, '
                     'METH_VARARGS|METH_KEYWORDS}},' % (
            globalobject_name,
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
    g = targetdir.join('frozen.py').open('w')
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
    for publicname, pyobjptr in exports.items():
        # some fishing needed to find the name of the obj
        pyobjnode = database.containernodes[pyobjptr._obj]
        print >> f, '\tPyModule_AddObject(m, "%s", %s);' % (publicname,
                                                            pyobjnode.name)
    print >> f, '}'
    f.close()

    #
    # Generate a setup.py while we're at it
    #
    pypy_include_dir = autopath.this_dir
    f = targetdir.join('setup.py').open('w')
    f.write(SETUP_PY % locals())
    f.close()

    return filename


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
