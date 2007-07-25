import autopath

import os, sys, inspect, re, imp
from pypy.translator.tool import stdoutcapture

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("cbuild")
py.log.setconsumer("cbuild", ansi_log)

debug = 0

def make_module_from_pyxstring(name, dirpath, string):
    dirpath = py.path.local(dirpath)
    pyxfile = dirpath.join('%s.pyx' % name) 
    i = 0
    while pyxfile.check():
        pyxfile = pyxfile.new(basename='%s%d.pyx' % (name, i))
        i+=1
    pyxfile.write(string)
    if debug: print "made pyxfile", pyxfile
    cfile = make_c_from_pyxfile(pyxfile)
    module = make_module_from_c(cfile)
    #print "made module", module
    return module

def compiler_command():
    # e.g. for tcc, you might set this to
    #    "tcc -shared -o %s.so %s.c"
    return os.getenv('PYPY_CC')

def enable_fast_compilation():
    if sys.platform == 'win32':
        dash = '/'
    else:
        dash = '-'
    from distutils import sysconfig
    gcv = sysconfig.get_config_vars()
    opt = gcv.get('OPT') # not always existent
    if opt:
        opt = re.sub('%sO\d+' % dash, '%sO0' % dash, opt)
    else:
        opt = '%sO0' % dash
    gcv['OPT'] = opt

def ensure_correct_math():
    if sys.platform != 'win32':
        return # so far
    from distutils import sysconfig
    gcv = sysconfig.get_config_vars()
    opt = gcv.get('OPT') # not always existent
    if opt and '/Op' not in opt:
        opt += '/Op'
    gcv['OPT'] = opt

def compile_c_module(cfiles, modname, include_dirs=None, libraries=[]):
    #try:
    #    from distutils.log import set_threshold
    #    set_threshold(10000)
    #except ImportError:
    #    print "ERROR IMPORTING"
    #    pass
    if include_dirs is None:
        include_dirs = []

    library_dirs = []
    if sys.platform == 'darwin':    # support Fink & Darwinports
        for s in ('/sw/', '/opt/local/'):
            if s + 'include' not in include_dirs and \
               os.path.exists(s + 'include'):
                include_dirs.append(s + 'include')
            if s + 'lib' not in library_dirs and \
               os.path.exists(s + 'lib'):
                library_dirs.append(s + 'lib')

    dirpath = cfiles[0].dirpath()
    lastdir = dirpath.chdir()
    ensure_correct_math()
    try:
        if debug: print "modname", modname
        c = stdoutcapture.Capture(mixed_out_err = True)
        try:
            try:
                if compiler_command():
                    # GCC-ish options only
                    from distutils import sysconfig
                    gcv = sysconfig.get_config_vars()
                    cmd = compiler_command().replace('%s',
                                                     str(dirpath.join(modname)))
                    for dir in [gcv['INCLUDEPY']] + list(include_dirs):
                        cmd += ' -I%s' % dir
                    os.system(cmd)
                else:
                    from distutils.dist import Distribution
                    from distutils.extension import Extension
                    from distutils.ccompiler import get_default_compiler
                    saved_environ = os.environ.items()
                    try:
                        # distutils.core.setup() is really meant for end-user
                        # interactive usage, because it eats most exceptions and
                        # turn them into SystemExits.  Instead, we directly
                        # instantiate a Distribution, which also allows us to
                        # ignore unwanted features like config files.
                        extra_compile_args = []
                        # ensure correct math on windows
                        if sys.platform == 'win32':
                            extra_compile_args.append('/Op') # get extra precision
                        if get_default_compiler() == 'unix':
                            old_version = False
                            try:
                                g = os.popen('gcc --version', 'r')
                                verinfo = g.read()
                                g.close()
                            except (OSError, IOError):
                                pass
                            else:
                                old_version = verinfo.startswith('2')
                            if not old_version:
                                extra_compile_args.extend(["-Wno-unused-label",
                                                        "-Wno-unused-variable"])
                        attrs = {
                            'name': "testmodule",
                            'ext_modules': [
                                Extension(modname, [str(cfile) for cfile in cfiles],
                                    include_dirs=include_dirs,
                                    library_dirs=library_dirs,
                                    extra_compile_args=extra_compile_args,
                                    libraries=libraries,)
                                ],
                            'script_name': 'setup.py',
                            'script_args': ['-q', 'build_ext', '--inplace'],
                            }
                        dist = Distribution(attrs)
                        if not dist.parse_command_line():
                            raise ValueError, "distutils cmdline parse error"
                        dist.run_commands()
                    finally:
                        for key, value in saved_environ:
                            if os.environ.get(key) != value:
                                os.environ[key] = value
            finally:
                foutput, foutput = c.done()
                data = foutput.read()
                if data:
                    fdump = open("%s.errors" % modname, "w")
                    fdump.write(data)
                    fdump.close()
            # XXX do we need to do some check on fout/ferr?
            # XXX not a nice way to import a module
        except:
            print >>sys.stderr, data
            raise
    finally:
        lastdir.chdir()

def cache_c_module(cfiles, modname, cache_dir=None,
                   include_dirs=None, libraries=[]):
    """ Same as build c module, but instead caches results and
    checks timestamps (eventually, not supported yet)
    """
    from pypy.tool.autopath import pypydir
    if cache_dir is None:
        cache_dir = py.path.local(pypydir).join('_cache')
    else:
        cache_dir = py.path.local(cache_dir)
    if cache_dir.check(dir=1):
        # XXX check timestamps of all cfiles
        if not cache_dir.join(modname + '.so').check():
            modname = str(cache_dir.join(modname))
            compile_c_module(cfiles, modname, include_dirs=include_dirs,
                             libraries=libraries)
            

def make_module_from_c(cfile, include_dirs=None, libraries=[]):
    cfile = py.path.local(cfile)
    modname = cfile.purebasename
    compile_c_module([cfile], modname, include_dirs, libraries)
    return import_module_from_directory(cfile.dirpath(), modname)

def import_module_from_directory(dir, modname):
    file, pathname, description = imp.find_module(modname, [str(dir)])
    try:
        mod = imp.load_module(modname, file, pathname, description)
    finally:
        if file:
            file.close()
    return mod

def make_c_from_pyxfile(pyxfile):
    from pypy.translator.pyrex import genpyrex
    pyrexdir = os.path.dirname(genpyrex.__file__)
    if pyrexdir not in sys.path:
        sys.path.insert(0, pyrexdir)
    from Pyrex.Compiler.Main import CompilationOptions, Context, PyrexError
    try:
        options = CompilationOptions(show_version = 0, 
                                     use_listing_file = 0, 
                                     c_only = 1,
                                     output_file = None)
        context = Context(options.include_path)
        result = context.compile(str(pyxfile), options)
        if result.num_errors > 0:
            raise ValueError, "failure %s" % result
    except PyrexError, e:
        print >>sys.stderr, e
    cfile = pyxfile.new(ext='.c')
    return cfile

def build_cfunc(func, simplify=1, dot=1, inputargtypes=None):
    """ return a pyrex-generated cfunction from the given func. 

    simplify is true -> perform simplifications on the flowgraph.
    dot is true      -> generate a dot-configuration file and postscript.
    inputargtypes is a list (allowed to be empty) ->
                        then annotation will be performed before generating 
                        dot/pyrex/c code. 

    """
    try: func = func.im_func
    except AttributeError: pass

    # build the flow graph
    from pypy.objspace.flow import Space
    from pypy.tool.udir import udir
    space = Space()
    name = func.func_name
    funcgraph = space.build_flow(func)

    if not inputargtypes: 
        source = inspect.getsource(func)
        base = udir.join(name).new(ext='.py').write(source) 

    if dot:
        from pypy.translator.tool.make_dot import FlowGraphDotGen
        dotgen = FlowGraphDotGen(name)
        dotgen.emit_subgraph(name, funcgraph)

    # apply transformations 
    if simplify:
        from pypy.translator.simplify import simplify_graph
        simplify_graph(funcgraph)
        name += '_s'

    # get the pyrex generator
    from pypy.translator.pyrex.genpyrex import GenPyrex
    genpyrex = GenPyrex(funcgraph)

    # generate pyrex (without type inference)

    # apply type inference 
    if inputargtypes is not None:
        genpyrex.annotate(inputargtypes)
        name += '_t'
        #a = Annotator(self.functiongraph)
        #a.build_types(input_arg_types)
        #a.simplify()

        pyxstring = genpyrex.emitcode()
        #funcgraph.source = inspect.getsource(func)
    else:
        pyxstring = genpyrex.emitcode()

    pyxheader = genpyrex.globaldeclarations()
    mod = make_module_from_pyxstring(name, udir, pyxheader + '\n' + pyxstring)

    if dot:
        if name != func.func_name:  # if some transformations have been done
            dotgen.emit_subgraph(name, funcgraph)
        dotgen.generate()
    return getattr(mod, func.func_name)


def log_spawned_cmd(spawn):
    def spawn_and_log(cmd, *args, **kwds):
        log.execute(' '.join(cmd))
        return spawn(cmd, *args, **kwds)
    return spawn_and_log


class ProfOpt(object):
    #XXX assuming gcc style flags for now
    name = "profopt"
    
    def __init__(self, compiler):
        self.compiler = compiler

    def first(self):
        self.build('-fprofile-generate')

    def probe(self, exe, args):
        # 'args' is a single string typically containing spaces
        # and quotes, which represents several arguments.
        os.system("'%s' %s" % (exe, args))

    def after(self):
        self.build('-fprofile-use')

    def build(self, option):
        compiler = self.compiler
        compiler.compile_extra.append(option)
        compiler.link_extra.append(option)
        try:
            compiler._build()
        finally:
            compiler.compile_extra.pop()
            compiler.link_extra.pop()
            
class CCompiler:

    def __init__(self, cfilenames, outputfilename=None, include_dirs=[],
                 libraries=[], library_dirs=[], compiler_exe=None,
                 profbased=None):
        self.cfilenames = cfilenames
        ext = ''
        self.compile_extra = []
        self.link_extra = []
        self.libraries = list(libraries)
        self.include_dirs = list(include_dirs)
        self.library_dirs = list(library_dirs)
        self.compiler_exe = compiler_exe
        self.profbased = profbased
        if not sys.platform in ('win32', 'darwin'): # xxx
            if 'm' not in self.libraries:
                self.libraries.append('m')
            if 'pthread' not in self.libraries:
                self.libraries.append('pthread')
            self.compile_extra += ['-O2', '-pthread']
            self.link_extra += ['-pthread']
        if sys.platform == 'win32':
            self.link_extra += ['/DEBUG'] # generate .pdb file
        if sys.platform == 'darwin':
            # support Fink & Darwinports
            for s in ('/sw/', '/opt/local/'):
                if s + 'include' not in self.include_dirs and \
                   os.path.exists(s + 'include'):
                    self.include_dirs.append(s + 'include')
                if s + 'lib' not in self.library_dirs and \
                   os.path.exists(s + 'lib'):
                    self.library_dirs.append(s + 'lib')
            self.compile_extra += ['-O2']

        if outputfilename is None:
            self.outputfilename = py.path.local(cfilenames[0]).new(ext=ext)
        else: 
            self.outputfilename = py.path.local(outputfilename) 

    def build(self, noerr=False):
        basename = self.outputfilename.new(ext='')
        try:
            try:
                c = stdoutcapture.Capture(mixed_out_err = True)
                if self.profbased is None:
                    self._build()
                else:
                    ProfDriver, args = self.profbased
                    profdrv = ProfDriver(self)
                    dolog = getattr(log, profdrv.name)
                    dolog(args)
                    profdrv.first()
                    dolog('Gathering profile data from: %s %s' % (
                           str(self.outputfilename), args))
                    profdrv.probe(str(self.outputfilename),args)
                    profdrv.after()
            finally:
                foutput, foutput = c.done()
                data = foutput.read()
                if data:
                    fdump = basename.new(ext='errors').open("w")
                    fdump.write(data)
                    fdump.close()
        except:
            if not noerr:
                print >>sys.stderr, data
            raise
 
    def _build(self):
        from distutils.ccompiler import new_compiler 
        compiler = new_compiler(force=1)
        if self.compiler_exe is not None:
            for c in '''compiler compiler_so compiler_cxx
                        linker_exe linker_so'''.split():
                compiler.executables[c][0] = self.compiler_exe
        compiler.spawn = log_spawned_cmd(compiler.spawn)
        objects = []
        for cfile in self.cfilenames: 
            cfile = py.path.local(cfile)
            old = cfile.dirpath().chdir() 
            try: 
                res = compiler.compile([cfile.basename], 
                                       include_dirs=self.include_dirs,
                                       extra_preargs=self.compile_extra)
                assert len(res) == 1
                cobjfile = py.path.local(res[0]) 
                assert cobjfile.check()
                objects.append(str(cobjfile))
            finally: 
                old.chdir() 
        compiler.link_executable(objects, str(self.outputfilename),
                                 libraries=self.libraries,
                                 extra_preargs=self.link_extra,
                                 library_dirs=self.library_dirs)

def build_executable(*args, **kwds):
    noerr = kwds.pop('noerr', False)
    compiler = CCompiler(*args, **kwds)
    compiler.build(noerr=noerr)
    return str(compiler.outputfilename)

def check_boehm_presence():
    from pypy.tool.udir import udir
    try:
        cfile = udir.join('check_boehm.c')
        cfname = str(cfile)
        cfile = cfile.open('w')
        cfile.write("""
#include <gc/gc.h>

int main() {
  return 0;
}
""")
        cfile.close()
        if sys.platform == 'win32':
            build_executable([cfname], libraries=['gc_pypy'], noerr=True)
        else:
            build_executable([cfname], libraries=['gc'], noerr=True)
    except:
        return False
    else:
        return True

def check_under_under_thread():
    from pypy.tool.udir import udir
    cfile = py.path.local(autopath.this_dir).join('__thread_test.c')
    fsource = cfile.open('r')
    source = fsource.read()
    fsource.close()
    cfile = udir.join('__thread_test.c')
    fsource = cfile.open('w')
    fsource.write(source)
    fsource.close()
    try:
       exe = build_executable([str(cfile)], 
                              noerr=True)
       py.process.cmdexec(exe)
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        return False
    else:
        return True
