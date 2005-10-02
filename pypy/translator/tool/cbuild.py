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

def compile_c_module(cfile, modname, include_dirs=None, libraries=[]):
    #try:
    #    from distutils.log import set_threshold
    #    set_threshold(10000)
    #except ImportError:
    #    print "ERROR IMPORTING"
    #    pass
    if include_dirs is None:
        include_dirs = []

    dirpath = cfile.dirpath()
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
                            extra_compile_args.append('/Op')
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
                                Extension(modname, [str(cfile)],
                                    include_dirs=include_dirs,
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

def make_module_from_c(cfile, include_dirs=None):
    cfile = py.path.local(cfile)
    modname = cfile.purebasename
    compile_c_module(cfile, modname, include_dirs)
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

def skip_missing_compiler(fn, *args, **kwds):
    from distutils.errors import DistutilsPlatformError
    try:
        return fn(*args, **kwds)
    except DistutilsPlatformError, e:
        py.test.skip('DistutilsPlatformError: %s' % (e,))

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

def build_executable(cfilenames, outputfilename=None, include_dirs=None,
                     libraries=[]):
    from distutils.ccompiler import new_compiler 
    ext = ''
    extra_preargs = None
    if sys.platform != 'win32': 
        libraries.append('m')
        libraries.append('pthread')
        extra_preargs = ['-O2', '-pthread']   # XXX 2 x hackish
    if outputfilename is None:
        outputfilename = py.path.local(cfilenames[0]).new(ext=ext)
    else: 
        outputfilename = py.path.local(outputfilename) 

    compiler = new_compiler()
    compiler.spawn = log_spawned_cmd(compiler.spawn)
    objects = []
    for cfile in cfilenames: 
        cfile = py.path.local(cfile)
        old = cfile.dirpath().chdir() 
        try: 
            res = compiler.compile([cfile.basename], 
                                   include_dirs=include_dirs,
                                   extra_preargs=extra_preargs)
            assert len(res) == 1
            cobjfile = py.path.local(res[0]) 
            assert cobjfile.check()
            objects.append(str(cobjfile))
        finally: 
            old.chdir() 
    compiler.link_executable(objects, str(outputfilename),
                             libraries=libraries,
                             extra_preargs=extra_preargs)
    return str(outputfilename)

def check_boehm_presence():
    from pypy.tool.udir import udir
    try:
        cfile = udir.join('check_boehm.c')
        cfname = str(cfile)
        cfile = cfile.open('w')
        cfile.write("""
#include <gc.h>

int main() {
  return 0;
}
""")
        cfile.close()
        build_executable([cfname], libraries=['gc'])
    except:
        return False
    else:
        return True
