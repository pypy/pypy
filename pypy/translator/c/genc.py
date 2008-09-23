import autopath
import py
import sys, os
from pypy.translator.c.node import PyObjectNode, FuncNode
from pypy.translator.c.database import LowLevelDatabase
from pypy.translator.c.extfunc import pre_include_code_lines
from pypy.translator.llsupport.wrapper import new_wrapper
from pypy.translator.gensupp import uniquemodulename, NameManager
from pypy.translator.tool.cbuild import so_ext, ExternalCompilationInfo
from pypy.translator.tool.cbuild import compile_c_module
from pypy.translator.tool.cbuild import CCompiler, ProfOpt
from pypy.translator.tool.cbuild import import_module_from_directory
from pypy.translator.tool.cbuild import check_under_under_thread
from pypy.rpython.lltypesystem import lltype
from pypy.tool.udir import udir
from pypy.tool import isolate
from pypy.translator.c.support import log, c_string_constant
from pypy.rpython.typesystem import getfunctionptr
from pypy.translator.c import gc

class CBuilder(object):
    c_source_filename = None
    _compiled = False
    modulename = None
    
    def __init__(self, translator, entrypoint, config, gcpolicy=None):
        self.translator = translator
        self.entrypoint = entrypoint
        self.entrypoint_name = self.entrypoint.func_name
        self.originalentrypoint = entrypoint
        self.config = config
        self.gcpolicy = gcpolicy    # for tests only, e.g. rpython/memory/
        if gcpolicy is not None and gcpolicy.requires_stackless:
            config.translation.stackless = True
        self.eci = ExternalCompilationInfo()

    def build_database(self):
        translator = self.translator

        gcpolicyclass = self.get_gcpolicyclass()

        if self.config.translation.gcrootfinder == "asmgcc":
            if not self.standalone:
                raise NotImplementedError("--gcrootfinder=asmgcc requires standalone")

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
                              thread_enabled=self.config.translation.thread,
                              sandbox=self.config.translation.sandbox)
        self.db = db
        
        # give the gc a chance to register interest in the start-up functions it
        # need (we call this for its side-effects of db.get())
        list(db.gcpolicy.gc_startup_code())

        # build entrypoint and eventually other things to expose
        pf = self.getentrypointptr()
        pfname = db.get(pf)
        self.c_entrypoint_name = pfname
        db.complete()

        self.collect_compilation_info(db)
        return db

    have___thread = None

    def collect_compilation_info(self, db):
        # we need a concrete gcpolicy to do this
        self.eci = self.eci.merge(ExternalCompilationInfo(
            libraries=db.gcpolicy.gc_libraries()))

        all = []
        for node in self.db.globalcontainers():
            eci = getattr(node, 'compilation_info', None)
            if eci:
                all.append(eci)
        self.eci = self.eci.merge(*all)

    def get_gcpolicyclass(self):
        if self.gcpolicy is None:
            name = self.config.translation.gctransformer
            if self.config.translation.gcrootfinder == "llvmgc":
                name = "%s+llvmgcroot" % (name,)
            elif self.config.translation.gcrootfinder == "asmgcc":
                name = "%s+asmgcroot" % (name,)
            return gc.name_to_gcpolicy[name]
        return self.gcpolicy

    # use generate_source(defines=DEBUG_DEFINES) to force the #definition
    # of the macros that enable debugging assertions
    DEBUG_DEFINES = {'RPY_ASSERT': 1,
                     'RPY_LL_ASSERT': 1}

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
        if self.config.translation.sandbox:
            defines['RPY_SANDBOXED'] = 1
        if CBuilder.have___thread is None:
            CBuilder.have___thread = check_under_under_thread()
        if not self.standalone:
            assert not self.config.translation.instrument
            cfile, extra = gen_source(db, modulename, targetdir, self.eci,
                                      defines = defines)
        else:
            if self.config.translation.instrument:
                defines['INSTRUMENT'] = 1
            if CBuilder.have___thread:
                if not self.config.translation.no__thread:
                    defines['USE___THREAD'] = 1
            # explicitely include python.h and exceptions.h
            # XXX for now, we always include Python.h
            from distutils import sysconfig
            python_inc = sysconfig.get_python_inc()
            pypy_include_dir = autopath.this_dir
            self.eci = self.eci.merge(ExternalCompilationInfo(
                include_dirs=[python_inc, pypy_include_dir],
            ))
            cfile, extra = gen_source_standalone(db, modulename, targetdir,
                                                 self.eci,
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
        graphs = db.all_graphs()
        db.gctransformer.prepare_inline_helpers(graphs)
        for node in db.containerlist:
            if isinstance(node, FuncNode):
                for funcgen in node.funcgens:
                    funcgen.patch_graph(copy_graph=False)
        return db


class ModuleWithCleanup(object):
    def __init__(self, mod):
        self.__dict__['mod'] = mod

    def __getattr__(self, name):
        mod = self.__dict__['mod']
        return getattr(mod, name)

    def __setattr__(self, name, val):
        mod = self.__dict__['mod']
        setattr(mod, name, val)

    def __del__(self):
        import sys
        if sys.platform == "win32":
            from _ctypes import FreeLibrary as dlclose
        else:
            from _ctypes import dlclose
        # XXX fish fish fish
        mod = self.__dict__['mod']
        dlclose(mod._lib._handle)
        try:
            del sys.modules[mod.__name__]
        except KeyError:
            pass


class CExtModuleBuilder(CBuilder):
    standalone = False
    _module = None
    _wrapper = None

    def getentrypointptr(self): # xxx
        if self._wrapper is None:
            self._wrapper = new_wrapper(self.entrypoint, self.translator)
        return self._wrapper

    def compile(self):
        assert self.c_source_filename 
        assert not self._compiled
        export_symbols = [self.db.get(self.getentrypointptr()),
                          'RPython_StartupCode',
                          ]
        if self.config.translation.countmallocs:
            export_symbols.append('malloc_counters')
        extsymeci = ExternalCompilationInfo(export_symbols=export_symbols)
        self.eci = self.eci.merge(extsymeci)
        compile_c_module([self.c_source_filename] + self.extrafiles,
                         self.c_source_filename.purebasename, self.eci,
                         tmpdir=self.c_source_filename.dirpath())
        self._compiled = True

    def _make_wrapper_module(self):
        fname = 'wrap_' + self.c_source_filename.purebasename
        modfile = self.c_source_filename.new(purebasename=fname, ext=".py")

        entrypoint_ptr = self.getentrypointptr()
        wrapped_entrypoint_c_name = self.db.get(entrypoint_ptr)
        
        CODE = """
import ctypes

_lib = ctypes.PyDLL(r"%(so_name)s")

_entry_point = getattr(_lib, "%(c_entrypoint_name)s")
_entry_point.restype = ctypes.py_object
_entry_point.argtypes = %(nargs)d*(ctypes.py_object,)

def entrypoint(*args):
    return _entry_point(*args)

try:
    _malloc_counters = _lib.malloc_counters
except AttributeError:
    pass
else:
    _malloc_counters.restype = ctypes.py_object
    _malloc_counters.argtypes = 2*(ctypes.py_object,)

    def malloc_counters():
        return _malloc_counters(None, None)

_rpython_startup = _lib.RPython_StartupCode
_rpython_startup()
""" % {'so_name': self.c_source_filename.new(ext=so_ext),
       'c_entrypoint_name': wrapped_entrypoint_c_name,
       'nargs': len(lltype.typeOf(entrypoint_ptr).TO.ARGS)}
        modfile.write(CODE)
        self._module_path = modfile
       
    def _import_module(self, isolated=False):
        if self._module is not None:
            return self._module
        assert self._compiled
        assert not self._module
        self._make_wrapper_module()
        if not isolated:
            mod = ModuleWithCleanup(self._module_path.pyimport())
        else:
            mod = isolate.Isolate((str(self._module_path.dirpath()),
                                   self._module_path.purebasename))
        self._module = mod
        return mod
        
    def get_entry_point(self, isolated=False):
        self._import_module(isolated=isolated)
        return getattr(self._module, "entrypoint")

    def get_malloc_counters(self, isolated=False):
        self._import_module(isolated=isolated)
        return self._module.malloc_counters
                       
    def cleanup(self):
        #assert self._module
        if isinstance(self._module, isolate.Isolate):
            isolate.close_isolate(self._module)

class CStandaloneBuilder(CBuilder):
    standalone = True
    executable_name = None

    def getprofbased(self):
        profbased = None
        if self.config.translation.instrumentctl is not None:
            profbased = self.config.translation.instrumentctl
        else:
            # xxx handling config.translation.profopt is a bit messy, because
            # it could be an empty string (not to be confused with None) and
            # because noprofopt can be used as an override.
            profopt = self.config.translation.profopt
            if profopt is not None and not self.config.translation.noprofopt:
                profbased = (ProfOpt, profopt)
        return profbased

    def has_profopt(self):
        profbased = self.getprofbased()
        return (profbased and isinstance(profbased, tuple)
                and profbased[0] is ProfOpt)

    def getentrypointptr(self):
        # XXX check that the entrypoint has the correct
        # signature:  list-of-strings -> int
        bk = self.translator.annotator.bookkeeper
        return getfunctionptr(bk.getdesc(self.entrypoint).getuniquegraph())

    def getccompiler(self):
        cc = self.config.translation.cc
        # Copy extrafiles to target directory, if needed
        extrafiles = []
        for fn in self.extrafiles:
            fn = py.path.local(fn)
            if not fn.relto(udir):
                newname = self.targetdir.join(fn.basename)
                fn.copy(newname)
                fn = newname
            extrafiles.append(fn)

        return CCompiler(
            [self.c_source_filename] + extrafiles,
            self.eci, compiler_exe = cc, profbased = self.getprofbased())

    def compile(self):
        assert self.c_source_filename
        assert not self._compiled
        compiler = self.getccompiler()
        if self.config.translation.gcrootfinder == "asmgcc":
            # as we are gcc-only anyway, let's just use the Makefile.
            cmdline = "make -C '%s'" % (self.targetdir,)
            err = os.system(cmdline)
            if err != 0:
                raise OSError("failed (see output): " + cmdline)
        else:
            eci = self.eci.merge(ExternalCompilationInfo(includes=
                                                         [str(self.targetdir)]))
            self.adaptflags(compiler)
            compiler.build()
        self.executable_name = str(compiler.outputfilename)
        self._compiled = True
        return self.executable_name

    def cmdexec(self, args=''):
        assert self._compiled
        return py.process.cmdexec('"%s" %s' % (self.executable_name, args))

    def adaptflags(self, compiler):
        if sys.platform == 'darwin':
            compiler.compile_extra.append('-mdynamic-no-pic')
        if sys.platform == 'sunos5':
            compiler.link_extra.append("-lrt")
        if self.config.translation.compilerflags:
            compiler.compile_extra.append(self.config.translation.compilerflags)
        if self.config.translation.linkerflags:
            compiler.link_extra.append(self.config.translation.linkerflags)

    def gen_makefile(self, targetdir):
        def write_list(lst, prefix):
            for i, fn in enumerate(lst):
                print >> f, prefix, fn,
                if i < len(lst)-1:
                    print >> f, '\\'
                else:
                    print >> f
                prefix = ' ' * len(prefix)

        self.eci = self.eci.merge(ExternalCompilationInfo(
            includes=['.', str(self.targetdir)]))
        compiler = self.getccompiler()
       
        self.adaptflags(compiler)
        assert self.config.translation.gcrootfinder != "llvmgc"
        cfiles = []
        ofiles = []
        gcmapfiles = []
        for fn in compiler.cfilenames:
            fn = py.path.local(fn)
            if fn.dirpath() == targetdir:
                name = fn.basename
            else:
                assert fn.dirpath().dirpath() == udir
                name = '../' + fn.relto(udir)
                
            name = name.replace("\\", "/")
            cfiles.append(name)
            if self.config.translation.gcrootfinder == "asmgcc":
                ofiles.append(name[:-2] + '.s')
                gcmapfiles.append(name[:-2] + '.gcmap')
            else:
                ofiles.append(name[:-2] + '.o')

        if self.config.translation.cc:
            cc = self.config.translation.cc
        else:
            cc = self.eci.platform.get_compiler()
            if cc is None:
                cc = 'gcc'
        make_no_prof = ''
        if self.has_profopt():
            profopt = self.config.translation.profopt
            default_target = 'profopt'
            # XXX horrible workaround for a bug of profiling in gcc on
            # OS X with functions containing a direct call to fork()
            non_profilable = []
            assert len(compiler.cfilenames) == len(ofiles)
            for fn, oname in zip(compiler.cfilenames, ofiles):
                fn = py.path.local(fn)
                if '/*--no-profiling-for-this-file!--*/' in fn.read():
                    non_profilable.append(oname)
            if non_profilable:
                make_no_prof = '$(MAKE) %s' % (' '.join(non_profilable),)
        else:
            profopt = ''
            default_target = '$(TARGET)'

        f = targetdir.join('Makefile').open('w')
        print >> f, '# automatically generated Makefile'
        print >> f
        print >> f, 'PYPYDIR =', autopath.pypydir
        print >> f
        print >> f, 'TARGET =', py.path.local(compiler.outputfilename).basename
        print >> f
        print >> f, 'DEFAULT_TARGET =', default_target
        print >> f
        write_list(cfiles, 'SOURCES =')
        print >> f
        if self.config.translation.gcrootfinder == "asmgcc":
            write_list(ofiles, 'ASMFILES =')
            write_list(gcmapfiles, 'GCMAPFILES =')
            print >> f, 'OBJECTS = $(ASMFILES) gcmaptable.s'
        else:
            print >> f, 'GCMAPFILES ='
            write_list(ofiles, 'OBJECTS =')
        print >> f
        def makerel(path):
            rel = py.path.local(path).relto(py.path.local(autopath.pypydir))
            if rel:
                return os.path.join('$(PYPYDIR)', rel)
            else:
                return path
        args = ['-l'+libname for libname in self.eci.libraries]
        print >> f, 'LIBS =', ' '.join(args)
        args = ['-L'+makerel(path) for path in self.eci.library_dirs]
        print >> f, 'LIBDIRS =', ' '.join(args)
        args = ['-I'+makerel(path) for path in self.eci.include_dirs]
        write_list(args, 'INCLUDEDIRS =')
        print >> f
        print >> f, 'CFLAGS  =', ' '.join(compiler.compile_extra)
        print >> f, 'LDFLAGS =', ' '.join(compiler.link_extra)
        if self.config.translation.thread:
            print >> f, 'TFLAGS  = ' + '-pthread'
        else:
            print >> f, 'TFLAGS  = ' + ''
        print >> f, 'PROFOPT = ' + profopt
        print >> f, 'MAKENOPROF = ' + make_no_prof
        print >> f, 'CC      = ' + cc
        print >> f
        print >> f, MAKEFILE.strip()
        f.close()


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
        gen_structdef(fi, database)
        fi.close()
        name = 'forwarddecl.h'
        fi = self.makefile(name)
        print >> f, '#include "%s"' % name
        gen_forwarddecl(fi, database)
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


def gen_structdef(f, database):
    structdeflist = database.getstructdeflist()
    print >> f, '/***********************************************************/'
    print >> f, '/***  Structure definitions                              ***/'
    print >> f
    for node in structdeflist:
        if hasattr(node, 'forward_decl'):
            if node.forward_decl:
                print >> f, node.forward_decl
        else:
            print >> f, '%s %s;' % (node.typetag, node.name)
    print >> f
    for node in structdeflist:
        for line in node.definition():
            print >> f, line

def gen_forwarddecl(f, database):
    print >> f, '/***********************************************************/'
    print >> f, '/***  Forward declarations                               ***/'
    print >> f
    for node in database.globalcontainers():
        for line in node.forward_declaration():
            print >> f, line

# this function acts as the fallback for small sources for now.
# Maybe we drop this completely if source splitting is the way
# to go. Currently, I'm quite fine with keeping a working fallback.
# XXX but we need to reduce code duplication.

def gen_readable_parts_of_main_c_file(f, database, preimplementationlines=[]):
    #
    # All declarations
    #
    print >> f
    gen_structdef(f, database)
    print >> f
    gen_forwarddecl(f, database)

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
    graphs = database.all_graphs()
    database.gctransformer.prepare_inline_helpers(graphs)
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

def gen_source_standalone(database, modulename, targetdir, eci,
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

    eci.write_c_header(fi)

    print >> fi, '#include "src/g_prerequisite.h"'

    for line in database.gcpolicy.pre_gc_code():
        print >> fi, line

    fi.close()

    preimplementationlines = list(
        pre_include_code_lines(database, database.translator.rtyper))

    #
    # 1) All declarations
    # 2) Implementation of functions and global structures and arrays
    #
    sg = SourceGenerator(database, preimplementationlines)
    sg.set_strategy(targetdir)
    database.prepare_inline_helpers()
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

    eci = eci.convert_sources_to_files(being_main=True)
    return filename, sg.getextrafiles() + list(eci.separate_module_files)


def gen_source(database, modulename, targetdir, eci, defines={}):
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

    eci.write_c_header(fi)
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

    gen_startupcode(f, database)
    f.close()

    #
    # Generate a setup.py while we're at it
    #
    pypy_include_dir = autopath.this_dir
    f = targetdir.join('setup.py').open('w')
    include_dirs = eci.include_dirs
    library_dirs = eci.library_dirs
    libraries = eci.libraries
    f.write(SETUP_PY % locals())
    f.close()
    eci = eci.convert_sources_to_files(being_main=True)

    return filename, sg.getextrafiles() + list(eci.separate_module_files)


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
                       include_dirs = (PYPY_INCLUDE_DIR,) + %(include_dirs)r,
                       library_dirs = %(library_dirs)r,
                          libraries = %(libraries)r)])
'''

MAKEFILE = '''

all: $(DEFAULT_TARGET)

$(TARGET): $(OBJECTS)
\t$(CC) $(LDFLAGS) $(TFLAGS) -o $@ $(OBJECTS) $(LIBDIRS) $(LIBS)

# -frandom-seed is only to try to be as reproducable as possible

%.o: %.c
\t$(CC) $(CFLAGS) -frandom-seed=$< -o $@ -c $< $(INCLUDEDIRS)

%.s: %.c
\t$(CC) $(CFLAGS) -frandom-seed=$< -o $@ -S $< $(INCLUDEDIRS)

%.gcmap: %.s
\t$(PYPYDIR)/translator/c/gcc/trackgcroot.py -t $< > $@ || (rm -f $@ && exit 1)

gcmaptable.s: $(GCMAPFILES)
\t$(PYPYDIR)/translator/c/gcc/trackgcroot.py $(GCMAPFILES) > $@ || (rm -f $@ && exit 1)

clean:
\trm -f $(OBJECTS) $(TARGET) $(GCMAPFILES) *.gc?? ../module_cache/*.gc??

clean_noprof:
\trm -f $(OBJECTS) $(TARGET) $(GCMAPFILES)

debug:
\t$(MAKE) CFLAGS="-g -DRPY_ASSERT" $(TARGET)

debug_exc:
\t$(MAKE) CFLAGS="-g -DRPY_ASSERT -DDO_LOG_EXC" $(TARGET)

debug_mem:
\t$(MAKE) CFLAGS="-g -DRPY_ASSERT -DTRIVIAL_MALLOC_DEBUG" $(TARGET)

no_obmalloc:
\t$(MAKE) CFLAGS="-g -DRPY_ASSERT -DNO_OBMALLOC" $(TARGET)

linuxmemchk:
\t$(MAKE) CFLAGS="-g -DRPY_ASSERT -DLINUXMEMCHK" $(TARGET)

llsafer:
\t$(MAKE) CFLAGS="-O2 -DRPY_LL_ASSERT" $(TARGET)

lldebug:
\t$(MAKE) CFLAGS="-g -DRPY_ASSERT -DRPY_LL_ASSERT" $(TARGET)

profile:
\t$(MAKE) CFLAGS="-g -pg $(CFLAGS)" LDFLAGS="-pg $(LDFLAGS)" $(TARGET)

# it seems that GNU Make < 3.81 has no function $(abspath)
ABS_TARGET = $(shell python -c "import sys,os; print os.path.abspath(sys.argv[1])" $(TARGET))

profopt:
\t$(MAKENOPROF)    # these files must be compiled without profiling
\t$(MAKE) CFLAGS="-fprofile-generate $(CFLAGS)" LDFLAGS="-fprofile-generate $(LDFLAGS)" $(TARGET)
\tcd $(PYPYDIR)/translator/goal && $(ABS_TARGET) $(PROFOPT)
\t$(MAKE) clean_noprof
\t$(MAKE) CFLAGS="-fprofile-use $(CFLAGS)" LDFLAGS="-fprofile-use $(LDFLAGS)" $(TARGET)
'''
