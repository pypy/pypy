import autopath
import os, py
from pypy.translator.c.node import PyObjectNode
from pypy.translator.c.database import LowLevelDatabase
from pypy.translator.c.extfunc import pre_include_code_lines
from pypy.translator.gensupp import uniquemodulename
from pypy.translator.tool.cbuild import compile_c_module
from pypy.translator.tool.cbuild import build_executable
from pypy.translator.tool.cbuild import import_module_from_directory
from pypy.rpython.rmodel import getfunctionptr
from pypy.rpython import lltype
from pypy.tool.udir import udir

class CBuilder: 
    c_source_filename = None
    _compiled = False
    symboltable = None
    
    def __init__(self, translator, gcpolicy=None, libraries=None):
        self.translator = translator
        self.gcpolicy = gcpolicy

        if libraries is None:
            libraries = []
        self.libraries = libraries        

    def generate_source(self):
        assert self.c_source_filename is None
        translator = self.translator
        pf = self.getentrypointptr()
        db = LowLevelDatabase(translator, standalone=self.standalone, gcpolicy=self.gcpolicy)

        # we need a concrete gcpolicy to do this        
        self.libraries += db.gcpolicy.gc_libraries()

        pfname = db.get(pf)
        db.complete()

        modulename = uniquemodulename('testing')
        targetdir = udir.ensure(modulename, dir=1)
        defines = {}
        # defines={'COUNT_OP_MALLOCS': 1}
        if not self.standalone:
            from pypy.translator.c.symboltable import SymbolTable
            self.symboltable = SymbolTable()
            cfile, extra = gen_source(db, modulename, targetdir,
                                      defines = defines,
                                      exports = {translator.entrypoint.func_name: pf},
                                      symboltable = self.symboltable)
        else:
            cfile, extra = gen_source_standalone(db, modulename, targetdir,
                                                 entrypointname = pfname,
                                                 defines = defines)
        self.c_source_filename = py.path.local(cfile)
        self.extrafiles = extra
        return cfile 


class CExtModuleBuilder(CBuilder):
    standalone = False
    c_ext_module = None 

    def getentrypointptr(self):
        return lltype.pyobjectptr(self.translator.entrypoint)

    def compile(self):
        assert self.c_source_filename 
        assert not self._compiled
        compile_c_module([self.c_source_filename] + self.extrafiles,
                         self.c_source_filename.purebasename,
                         include_dirs = [autopath.this_dir],
                         libraries=self.libraries)
        self._compiled = True

    def import_module(self):
        assert self._compiled
        assert not self.c_ext_module
        mod = import_module_from_directory(self.c_source_filename.dirpath(),
                                           self.c_source_filename.purebasename)
        self.c_ext_module = mod
        if self.symboltable:
            self.symboltable.attach(mod)   # hopefully temporary hack
        return mod
        
    def get_entry_point(self):
        assert self.c_ext_module 
        return getattr(self.c_ext_module, 
                       self.translator.entrypoint.func_name)


class CStandaloneBuilder(CBuilder):
    standalone = True
    executable_name = None

    def getentrypointptr(self):
        # XXX check that the entrypoint has the correct
        # signature:  list-of-strings -> int
        return getfunctionptr(self.translator, self.translator.entrypoint)

    def compile(self):
        assert self.c_source_filename
        assert not self._compiled
        # XXX for now, we always include Python.h
        from distutils import sysconfig
        python_inc = sysconfig.get_python_inc()
        self.executable_name = build_executable([self.c_source_filename],
                                         include_dirs = [autopath.this_dir,
                                                         python_inc],
                                         libraries=self.libraries)
        self._compiled = True
        return self.executable_name

    def cmdexec(self, args=''):
        assert self._compiled
        return py.process.cmdexec('"%s" %s' % (self.executable_name, args))


def translator2database(translator):
    pf = lltype.pyobjectptr(translator.entrypoint)
    db = LowLevelDatabase(translator)
    db.get(pf)
    db.complete()
    return db, pf

# ____________________________________________________________

class SourceGenerator:
    one_source_file = True

    def __init__(self, database, preimplementationlines=[]):
        self.database = database
        self.preimpl = preimplementationlines
        self.extrafiles = []
        self.path = None

    def set_strategy(self, path):
        #self.one_source_file = False
        # disabled for now, until all the includes are updated!
        self.path = path

    def makefile(self, name):
        filepath = self.path.join(name)
        if name.endswith('.c'):
            self.extrafiles.append(filepath)
        return filepath.open('w')

    def getextrafiles(self):
        return self.extrafiles

    def splitglobalcontainers(self):
        return [('theimplementations.c', self.database.globalcontainers())]

    def gen_readable_parts_of_source(self, f):
        if self.one_source_file:
            return gen_readable_parts_of_main_c_file(f, self.database,
                                                     self.preimpl)
        #
        # All declarations
        #
        database= self.database
        structdeflist = database.getstructdeflist()
        name = 'structdef.h'
        fi = self.makefile(name)
        print >> f, '#include "%s"' % name
        print >> fi, '/***********************************************************/'
        print >> fi, '/***  Structure definitions                              ***/'
        print >> fi
        for node in structdeflist:
            print >> fi, 'struct %s;' % node.name
        print >> fi
        for node in structdeflist:
            for line in node.definition(phase=1):
                print >> fi, line
        print >> fi
        print >> fi, '/***********************************************************/'
        fi.close()
        name = 'forwarddecl.h'
        fi = self.makefile(name)
        print >> f, '#include "%s"' % name
        print >> fi, '/***********************************************************/'
        print >> fi, '/***  Forward declarations                               ***/'
        print >> fi
        for node in database.globalcontainers():
            for line in node.forward_declaration():
                print >> fi, line
        print >> fi
        print >> fi, '/***********************************************************/'
        fi.close()

        #
        # Implementation of functions and global structures and arrays
        #
        print >> f
        print >> f, '/***********************************************************/'
        print >> f, '/***  Implementations                                    ***/'
        print >> f
        for line in self.preimpl:
            print >> f, line
        print >> f, '#include "src/g_include.h"'
        print >> f
        name = 'structimpl.c'
        print >> f, '/* %s */' % name
        fc = self.makefile(name)
        print >> fc, '/***********************************************************/'
        print >> fc, '/***  Structure Implementations                          ***/'
        print >> fc
        print >> fc, '#include "common_header.h"'
        print >> fc
        for node in structdeflist:
            for line in node.definition(phase=2):
                print >> fc, line
        print >> fc
        print >> fc, '/***********************************************************/'
        fc.close()
        for name, nodes in self.splitglobalcontainers():
            print >> f, '/* %s */' % name
            fc = self.makefile(name)
            print >> fc, '/***********************************************************/'
            print >> fc, '/***  Implementations                                    ***/'
            print >> fc
            print >> fc, '#include "common_header.h"'
            print >> fc, '#include "structdef.h"'
            print >> fc, '#include "forwarddecl.h"'
            print >> fc
            for line in self.preimpl:
                print >> fc, line
            print >> fc
            print >> fc, '#define PYPY_NOT_MAIN_FILE'
            print >> fc, '#include "src/g_include.h"'
            print >> fc
            for node in nodes:
                for line in node.implementation():
                    print >> fc, line
            print >> fc
            print >> fc, '/***********************************************************/'
            fc.close()
        print >> f

# this function acts as the fallback for small sources for now.
# Maybe we drop this completely if source splitting is the way
# to go. Currently, I'm quite fine with keeping a working fallback.

def gen_readable_parts_of_main_c_file(f, database, preimplementationlines=[]):
    #
    # All declarations
    #
    structdeflist = database.getstructdeflist()
    print >> f
    print >> f, '/***********************************************************/'
    print >> f, '/***  Structure definitions                              ***/'
    print >> f
    for node in structdeflist:
        print >> f, 'struct %s;' % node.name
    print >> f
    for node in structdeflist:
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
    for node in structdeflist:
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

def gen_startupcode(f, database):
    # generate the start-up code and put it into a function
    print >> f, 'char *RPython_StartupCode(void) {'
    print >> f, '\tchar *error = NULL;'
    for line in database.gcpolicy.gc_startup_code():
        print >> f,"\t" + line

    # put float infinities in global constants, we should not have so many of them for now to make
    # a table+loop preferable
    for dest, value in database.infs:
        print >> f, "\t%s = %s;" % (dest, value)

    firsttime = True
    for node in database.containerlist:
        lines = list(node.startupcode())
        if lines:
            if firsttime:
                firsttime = False
            else:
                print >> f, '\tif (error) return error;'
            for line in lines:
                print >> f, '\t'+line
    print >> f, '\treturn error;'
    print >> f, '}'

def gen_source_standalone(database, modulename, targetdir, 
                          entrypointname, defines={}): 
    assert database.standalone
    if isinstance(targetdir, str):
        targetdir = py.path.local(targetdir)
    filename = targetdir.join(modulename + '.c')
    f = filename.open('w')
    incfilename = targetdir.join('common_header.h')
    fi = incfilename.open('w')

    #
    # Header
    #
    print >> f, '#include "common_header.h"'
    print >> f
    defines['PYPY_STANDALONE'] = entrypointname
    for key, value in defines.items():
        print >> fi, '#define %s %s' % (key, value)

    print >> fi, '#define Py_BUILD_CORE  /* for Windows: avoid pulling libs in */'
    print >> fi, '#include "pyconfig.h"'
    for line in database.gcpolicy.pre_pre_gc_code():
        print >> fi, line

    print >> fi, '#include "src/g_prerequisite.h"'

    for line in database.gcpolicy.pre_gc_code():
        print >> fi, line

    includes = {}
    for node in database.globalcontainers():
        for include in node.includes:
            includes[include] = True
    includes = includes.keys()
    includes.sort()
    for include in includes:
        print >> fi, '#include <%s>' % (include,)
    fi.close()

    preimplementationlines = list(
        pre_include_code_lines(database, database.translator.rtyper))

    #
    # 1) All declarations
    # 2) Implementation of functions and global structures and arrays
    #
    sg = SourceGenerator(database, preimplementationlines)
    sg.set_strategy(targetdir)
    sg.gen_readable_parts_of_source(f)

    # 3) start-up code
    print >> f
    gen_startupcode(f, database)

    f.close()
    return filename, sg.getextrafiles()


def gen_source(database, modulename, targetdir, defines={}, exports={},
               symboltable=None):
    assert not database.standalone
    if isinstance(targetdir, str):
        targetdir = py.path.local(targetdir)
    filename = targetdir.join(modulename + '.c')
    f = filename.open('w')
    incfilename = targetdir.join('common_header.h')
    fi = incfilename.open('w')

    #
    # Header
    #
    print >> f, '#include "common_header.h"'
    print >> f
    for key, value in defines.items():
        print >> fi, '#define %s %s' % (key, value)

    print >> fi, '#include "pyconfig.h"'
    for line in database.gcpolicy.pre_pre_gc_code():
        print >> fi, line

    print >> fi, '#include "src/g_prerequisite.h"'

    for line in database.gcpolicy.pre_gc_code():
        print >> fi, line

    includes = {}
    for node in database.globalcontainers():
        for include in node.includes:
            includes[include] = True
    includes = includes.keys()
    includes.sort()
    for include in includes:
        print >> fi, '#include <%s>' % (include,)
    fi.close()

    if database.translator is None or database.translator.rtyper is None:
        preimplementationlines = []
    else:
        preimplementationlines = list(
            pre_include_code_lines(database, database.translator.rtyper))

    #
    # 1) All declarations
    # 2) Implementation of functions and global structures and arrays
    #
    sg = SourceGenerator(database, preimplementationlines)
    sg.set_strategy(targetdir)
    sg.gen_readable_parts_of_source(f)

    #
    # Debugging info
    #
    if symboltable:
        print >> f
        print >> f, '/*******************************************************/'
        print >> f, '/***  Debugging info                                 ***/'
        print >> f
        print >> f, 'static int debuginfo_offsets[] = {'
        for node in database.structdefnodes.values():
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
    gen_startupcode(f, database)
    print >> f
    print >> f, 'MODULE_INITFUNC(%s)' % modulename
    print >> f, '{'
    print >> f, '\tSETUP_MODULE(%s);' % modulename
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

    return filename, sg.getextrafiles()


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
