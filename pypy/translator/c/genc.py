import autopath
import py
from pypy.translator.c.node import PyObjectNode, PyObjHeadNode, FuncNode
from pypy.translator.c.database import LowLevelDatabase
from pypy.translator.c.extfunc import pre_include_code_lines
from pypy.translator.gensupp import uniquemodulename, NameManager
from pypy.translator.tool.cbuild import compile_c_module
from pypy.translator.tool.cbuild import build_executable, CCompiler, ProfOpt
from pypy.translator.tool.cbuild import import_module_from_directory
from pypy.translator.tool.cbuild import check_under_under_thread
from pypy.rpython.lltypesystem import lltype
from pypy.tool.udir import udir
from pypy.tool import isolate
from pypy.translator.locality.calltree import CallTree
from pypy.translator.c.support import log, c_string_constant
from pypy.rpython.typesystem import getfunctionptr
from pypy.translator.c import gc

class CBuilder(object):
    c_source_filename = None
    _compiled = False
    symboltable = None
    modulename = None
    
    def __init__(self, translator, entrypoint, config, libraries=None,
                 gcpolicy=None):
        self.translator = translator
        self.entrypoint = entrypoint
        self.originalentrypoint = entrypoint
        self.gcpolicy = gcpolicy
        if gcpolicy is not None and gcpolicy.requires_stackless:
            config.translation.stackless = True
        self.config = config

        if libraries is None:
            libraries = []
        self.libraries = libraries
        self.exports = {}

    def build_database(self, exports=[], pyobj_options=None):
        translator = self.translator

        gcpolicyclass = self.get_gcpolicyclass()

        if self.config.translation.stackless:
            if not self.standalone:
                raise Exception("stackless: only for stand-alone builds")
            
            from pypy.translator.stackless.transform import StacklessTransformer
            stacklesstransformer = StacklessTransformer(
                translator, self.originalentrypoint,
                stackless_gc=gcpolicyclass.requires_stackless)
            self.entrypoint = stacklesstransformer.slp_entry_point
        else:
            stacklesstransformer = None

        db = LowLevelDatabase(translator, standalone=self.standalone,
                              gcpolicyclass=gcpolicyclass,
                              stacklesstransformer=stacklesstransformer,
                              thread_enabled=self.config.translation.thread)
        # pass extra options into pyobjmaker
        if pyobj_options:
            for key, value in pyobj_options.items():
                setattr(db.pyobjmaker, key, value)

        # we need a concrete gcpolicy to do this
        self.libraries += db.gcpolicy.gc_libraries()

        # give the gc a chance to register interest in the start-up functions it
        # need (we call this for its side-effects of db.get())
        list(db.gcpolicy.gc_startup_code())

        # build entrypoint and eventually other things to expose
        pf = self.getentrypointptr()
        pfname = db.get(pf)
        self.exports[self.entrypoint.func_name] = pf
        for obj in exports:
            if type(obj) is tuple:
                objname, obj = obj
            elif hasattr(obj, '__name__'):
                objname = obj.__name__
            else:
                objname = None
            po = self.getentrypointptr(obj)
            poname = db.get(po)
            objname = objname or poname
            if objname in self.exports:
                raise NameError, 'duplicate name in export: %s is %s and %s' % (
                    objname, db.get(self.exports[objname]), poname)
            self.exports[objname] = po
        db.complete()

        # add library dependencies
        seen = dict.fromkeys(self.libraries)
        for node in db.globalcontainers():
            if hasattr(node, 'libraries'):
                for library in node.libraries:
                    if library not in seen:
                        self.libraries.append(library)
                        seen[library] = True
        return db

    have___thread = None


    def get_gcpolicyclass(self):
        if self.gcpolicy is None:
            return gc.name_to_gcpolicy[self.config.translation.gc]
        return self.gcpolicy

    def generate_source(self, db=None, defines={}):
        assert self.c_source_filename is None
        translator = self.translator

        if db is None:
            db = self.build_database()
        pf = self.getentrypointptr()
        pfname = db.get(pf)

        if self.modulename is None:
            self.modulename = uniquemodulename('testing')
        modulename = self.modulename
        targetdir = udir.ensure(modulename, dir=1)
        self.targetdir = targetdir
        defines = defines.copy()
        if self.config.translation.countmallocs:
            defines['COUNT_OP_MALLOCS'] = 1
        if CBuilder.have___thread is None:
            CBuilder.have___thread = check_under_under_thread()
        if not self.standalone:
            assert not self.config.translation.instrument
            from pypy.translator.c.symboltable import SymbolTable
            # XXX fix symboltable
            #self.symboltable = SymbolTable()
            cfile, extra = gen_source(db, modulename, targetdir,
                                      defines = defines,
                                      exports = self.exports,
                                      symboltable = self.symboltable)
        else:
            if self.config.translation.instrument:
                defines['INSTRUMENT'] = 1
            if CBuilder.have___thread:
                if not self.config.translation.no__thread:
                    defines['USE___THREAD'] = 1
            cfile, extra = gen_source_standalone(db, modulename, targetdir,
                                                 entrypointname = pfname,
                                                 defines = defines)
        self.c_source_filename = py.path.local(cfile)
        self.extrafiles = extra
        if self.standalone:
            self.gen_makefile(targetdir)
        return cfile

    def generate_graphs_for_llinterp(self, db=None):
        # prepare the graphs as when the source is generated, but without
        # actually generating the source.
        if db is None:
            db = self.build_database()
        for node in db.containerlist:
            if isinstance(node, FuncNode):
                for funcgen in node.funcgens:
                    funcgen.patch_graph(copy_graph=False)
        return db


class CExtModuleBuilder(CBuilder):
    standalone = False
    c_ext_module = None 

    def getentrypointptr(self, obj=None):
        if obj is None:
            obj = self.entrypoint
        return lltype.pyobjectptr(obj)

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

    def isolated_import(self):
        assert self._compiled
        assert not self.c_ext_module
        self.c_ext_module = isolate.Isolate((str(self.c_source_filename.dirpath()),
                                             self.c_source_filename.purebasename))
        return self.c_ext_module
        
    def get_entry_point(self):
        assert self.c_ext_module 
        return getattr(self.c_ext_module, 
                       self.entrypoint.func_name)

    def cleanup(self):
        assert self.c_ext_module
        if isinstance(self.c_ext_module, isolate.Isolate):
            isolate.close_isolate(self.c_ext_module)

class CStandaloneBuilder(CBuilder):
    standalone = True
    executable_name = None

    def getentrypointptr(self):
        # XXX check that the entrypoint has the correct
        # signature:  list-of-strings -> int
        bk = self.translator.annotator.bookkeeper
        return getfunctionptr(bk.getdesc(self.entrypoint).getuniquegraph())

    def getccompiler(self, extra_includes):
        # XXX for now, we always include Python.h
        from distutils import sysconfig
        python_inc = sysconfig.get_python_inc()
        cc = self.config.translation.cc
        profbased = None
        if self.config.translation.instrumentctl is not None:
            profbased = self.config.translation.instrumentctl
        else:
            profopt = self.config.translation.profopt
            if profopt is not None:
                profbased = (ProfOpt, profopt)

        return CCompiler(
            [self.c_source_filename] + self.extrafiles,
            include_dirs = [autopath.this_dir, python_inc] + extra_includes,
            libraries    = self.libraries,
            compiler_exe = cc, profbased = profbased)

    def compile(self):
        assert self.c_source_filename
        assert not self._compiled
        compiler = self.getccompiler(extra_includes=[str(self.targetdir)])
        if self.config.translation.compilerflags:
            compiler.compile_extra.append(self.config.translation.compilerflags)
        if self.config.translation.linkerflags:
            compiler.link_extra.append(self.config.translation.linkerflags)
        compiler.build()
        self.executable_name = str(compiler.outputfilename)
        self._compiled = True
        return self.executable_name

    def cmdexec(self, args=''):
        assert self._compiled
        return py.process.cmdexec('"%s" %s' % (self.executable_name, args))

    def gen_makefile(self, targetdir):
        def write_list(lst, prefix):
            for i, fn in enumerate(lst):
                print >> f, prefix, fn,
                if i < len(lst)-1:
                    print >> f, '\\'
                else:
                    print >> f
                prefix = ' ' * len(prefix)

        compiler = self.getccompiler(extra_includes=['.'])
        if self.config.translation.compilerflags:
            compiler.compile_extra.append(self.config.translation.compilerflags)
        if self.config.translation.linkerflags:
            compiler.link_extra.append(self.config.translation.linkerflags)
        cfiles = []
        ofiles = []
        for fn in compiler.cfilenames:
            fn = py.path.local(fn).basename
            assert fn.endswith('.c')
            cfiles.append(fn)
            ofiles.append(fn[:-2] + '.o')

        if self.config.translation.cc:
            cc = self.config.translation.cc
        else:
            cc = 'gcc'
        if self.config.translation.profopt:
            profopt = self.config.translation.profopt
        else:
            profopt = ''

        f = targetdir.join('Makefile').open('w')
        print >> f, '# automatically generated Makefile'
        print >> f
        print >> f, 'TARGET =', py.path.local(compiler.outputfilename).basename
        print >> f
        write_list(cfiles, 'SOURCES =')
        print >> f
        write_list(ofiles, 'OBJECTS =')
        print >> f
        args = ['-l'+libname for libname in compiler.libraries]
        print >> f, 'LIBS =', ' '.join(args)
        args = ['-L'+path for path in compiler.library_dirs]
        print >> f, 'LIBDIRS =', ' '.join(args)
        args = ['-I'+path for path in compiler.include_dirs]
        write_list(args, 'INCLUDEDIRS =')
        print >> f
        print >> f, 'CFLAGS  =', ' '.join(compiler.compile_extra)
        print >> f, 'LDFLAGS =', ' '.join(compiler.link_extra)
        if self.config.translation.thread:
            print >> f, 'TFLAGS  = ' + '-pthread'
        else:
            print >> f, 'TFLAGS  = ' + ''
        print >> f, 'PROFOPT = ' + profopt
        print >> f, 'CC      = ' + cc
        print >> f
        print >> f, MAKEFILE.strip()
        f.close()


def translator2database(translator, entrypoint):
    pf = lltype.pyobjectptr(entrypoint)
    db = LowLevelDatabase(translator)
    db.get(pf)
    db.complete()
    return db, pf

# ____________________________________________________________

SPLIT_CRITERIA = 65535 # support VC++ 7.2
#SPLIT_CRITERIA = 32767 # enable to support VC++ 6.0

MARKER = '/*/*/' # provide an easy way to split after generating

class SourceGenerator:
    one_source_file = True

    def __init__(self, database, preimplementationlines=[]):
        self.database = database
        self.preimpl = preimplementationlines
        self.extrafiles = []
        self.path = None
        self.namespace = NameManager()

    def set_strategy(self, path):
        all_nodes = list(self.database.globalcontainers())
        # split off non-function nodes. We don't try to optimize these, yet.
        funcnodes = []
        othernodes = []
        for node in all_nodes:
            if node.nodekind == 'func':
                funcnodes.append(node)
            else:
                othernodes.append(node)
        # for now, only split for stand-alone programs.
        if self.database.standalone:
            self.one_source_file = False
        self.funcnodes = funcnodes
        self.othernodes = othernodes
        self.path = path
        # disabled this for a while, does worsen things
#        graph = CallTree(self.funcnodes, self.database)
#        graph.simulate()
#        graph.optimize()
#        self.funcnodes = graph.ordered_funcnodes()

    def uniquecname(self, name):
        assert name.endswith('.c')
        return self.namespace.uniquename(name[:-2]) + '.c'

    def makefile(self, name):
        log.writing(name)
        filepath = self.path.join(name)
        if name.endswith('.c'):
            self.extrafiles.append(filepath)
        return filepath.open('w')

    def getextrafiles(self):
        return self.extrafiles

    def getothernodes(self):
        return self.othernodes[:]

    def splitnodesimpl(self, basecname, nodes, nextra, nbetween,
                       split_criteria=SPLIT_CRITERIA):
        # produce a sequence of nodes, grouped into files
        # which have no more than SPLIT_CRITERIA lines
        iternodes = iter(nodes)
        done = [False]
        def subiter():
            used = nextra
            for node in iternodes:
                impl = '\n'.join(list(node.implementation())).split('\n')
                if not impl:
                    continue
                cost = len(impl) + nbetween
                yield node, impl
                del impl
                if used + cost > split_criteria:
                    # split if criteria met, unless we would produce nothing.
                    raise StopIteration
                used += cost
            done[0] = True
        while not done[0]:
            yield self.uniquecname(basecname), subiter()

    def gen_readable_parts_of_source(self, f):
        if py.std.sys.platform != "win32":
            split_criteria_big = SPLIT_CRITERIA * 4 
        else:
            split_criteria_big = SPLIT_CRITERIA
        if self.one_source_file:
            return gen_readable_parts_of_main_c_file(f, self.database,
                                                     self.preimpl)
        #
        # All declarations
        #
        database = self.database
        structdeflist = database.getstructdeflist()
        name = 'structdef.h'
        fi = self.makefile(name)
        print >> f, '#include "%s"' % name
        print >> fi, '/***********************************************************/'
        print >> fi, '/***  Structure definitions                              ***/'
        print >> fi
        for node in structdeflist:
            if getattr(node, 'is_external', False):
                continue
            print >> fi, '%s %s;' % (node.typetag, node.name)
        print >> fi
        for node in structdeflist:
            for line in node.definition():
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
        name = self.uniquecname('structimpl.c')
        print >> f, '/* %s */' % name
        fc = self.makefile(name)
        print >> fc, '/***********************************************************/'
        print >> fc, '/***  Structure Implementations                          ***/'
        print >> fc
        print >> fc, '#define PYPY_NOT_MAIN_FILE'
        print >> fc, '#include "common_header.h"'
        print >> fc, '#include "structdef.h"'
        print >> fc, '#include "forwarddecl.h"'
        print >> fc
        print >> fc, '#include "src/g_include.h"'
        print >> fc
        print >> fc, MARKER

        print >> fc, '/***********************************************************/'
        fc.close()

        nextralines = 11 + 1
        for name, nodeiter in self.splitnodesimpl('nonfuncnodes.c',
                                                   self.othernodes,
                                                   nextralines, 1):
            print >> f, '/* %s */' % name
            fc = self.makefile(name)
            print >> fc, '/***********************************************************/'
            print >> fc, '/***  Non-function Implementations                       ***/'
            print >> fc
            print >> fc, '#define PYPY_NOT_MAIN_FILE'
            print >> fc, '#include "common_header.h"'
            print >> fc, '#include "structdef.h"'
            print >> fc, '#include "forwarddecl.h"'
            print >> fc
            print >> fc, '#include "src/g_include.h"'
            print >> fc
            print >> fc, MARKER
            for node, impl in nodeiter:
                print >> fc, '\n'.join(impl)
                print >> fc, MARKER
            print >> fc, '/***********************************************************/'
            fc.close()

        nextralines = 8 + len(self.preimpl) + 4 + 1
        for name, nodeiter in self.splitnodesimpl('implement.c',
                                                   self.funcnodes,
                                                   nextralines, 1,
                                                   split_criteria_big):
            print >> f, '/* %s */' % name
            fc = self.makefile(name)
            print >> fc, '/***********************************************************/'
            print >> fc, '/***  Implementations                                    ***/'
            print >> fc
            print >> fc, '#define PYPY_NOT_MAIN_FILE'
            print >> fc, '#include "common_header.h"'
            print >> fc, '#include "structdef.h"'
            print >> fc, '#include "forwarddecl.h"'
            print >> fc
            for line in self.preimpl:
                print >> fc, line
            print >> fc
            print >> fc, '#include "src/g_include.h"'
            print >> fc
            print >> fc, MARKER
            for node, impl in nodeiter:
                print >> fc, '\n'.join(impl)
                print >> fc, MARKER
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
        if node.name and not getattr(node, 'is_external', False):
            print >> f, '%s %s;' % (node.typetag, node.name)
    print >> f
    for node in structdeflist:
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
    print >> f
    for line in preimplementationlines:
        print >> f, line
    print >> f, '#include "src/g_include.h"'
    print >> f
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
    for dest, value in database.late_initializations:
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
        if hasattr(node, 'includes'):
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

    if 'INSTRUMENT' in defines:
        fi = incfilename.open('a')
        n = database.instrument_ncounter
        print >>fi, "#define INSTRUMENT_NCOUNTER %d" % n
        fi.close()
    
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
        if hasattr(node, 'includes'):
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
    for node in database.containerlist:
        if isinstance(node, (PyObjectNode, PyObjHeadNode)):
            for target in node.where_to_copy_me:
                print >> f, '\t{%s, "%s"},' % (target, node.exported_name)
    print >> f, '\t{ NULL, NULL }\t/* Sentinel */'
    print >> f, '};'
    print >> f
    print >> f, 'static cpyobjheaddef_t cpyobjheaddefs[] = {'
    for node in database.containerlist:
        if isinstance(node, PyObjHeadNode):
            print >> f, '\t{"%s", %s, %s},' % (node.exported_name,
                                               node.ptrname,
                                               node.get_setupfn_name())
    print >> f, '\t{ NULL, NULL, NULL }\t/* Sentinel */'
    print >> f, '};'
    print >> f
    print >> f, '/***********************************************************/'
    print >> f, '/***  Table of functions                                 ***/'
    print >> f
    print >> f, 'static globalfunctiondef_t globalfunctiondefs[] = {'
    wrappers = pyobjmaker.wrappers.items()
    wrappers.sort()
    for globalobject_name, (base_name, wrapper_name, func_doc) in wrappers:
        print >> f, ('\t{&%s, "%s", {"%s", (PyCFunction)%s, '
                     'METH_VARARGS|METH_KEYWORDS, %s}},' % (
            globalobject_name,
            globalobject_name,
            base_name,
            wrapper_name,
            func_doc and c_string_constant(func_doc) or 'NULL'))
    print >> f, '\t{ NULL }\t/* Sentinel */'
    print >> f, '};'
    print >> f, 'static globalfunctiondef_t *globalfunctiondefsptr = &globalfunctiondefs[0];'
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
    print >> f, '\tcall_postsetup(m);'
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

MAKEFILE = '''

$(TARGET): $(OBJECTS)
\t$(CC) $(LDFLAGS) $(TFLAGS) -o $@ $(OBJECTS) $(LIBDIRS) $(LIBS)

%.o: %.c
\t$(CC) $(CFLAGS) -o $@ -c $< $(INCLUDEDIRS)

clean:
\trm -f $(OBJECTS) $(TARGET)

debug:
\tmake CFLAGS="-g -DRPY_ASSERT"

debug_exc:
\tmake CFLAGS="-g -DRPY_ASSERT -DDO_LOG_EXC"

debug_mem:
\tmake CFLAGS="-g -DRPY_ASSERT -DNO_OBMALLOC"

profile:
\tmake CFLAGS="-g -pg $(CFLAGS)" LDFLAGS="-pg $(LDFLAGS)"

profopt:
\tmake CFLAGS="-fprofile-generate $(CFLAGS)" LDFLAGS="-fprofile-generate $(LDFLAGS)"
\t./$(TARGET) $(PROFOPT)
\trm -f $(OBJECTS) $(TARGET)
\tmake CFLAGS="-fprofile-use $(CFLAGS)" LDFLAGS="-fprofile-use $(LDFLAGS)"
'''
