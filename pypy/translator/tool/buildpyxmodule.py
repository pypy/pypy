import autopath
from pypy.tool import testit
from pypy.tool.udir import udir

from py.process import cmdexec 
from py import path 
from pypy.translator.genpyrex import GenPyrex

import os, sys, inspect
from pypy.translator.tool import stdoutcapture

debug = 0

def make_module_from_pyxstring(name, dirpath, string):
    dirpath = path.local(dirpath)
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

def make_module_from_c(cfile):
    from distutils.core import setup
    from distutils.extension import Extension

    #try:
    #    from distutils.log import set_threshold
    #    set_threshold(10000)
    #except ImportError:
    #    print "ERROR IMPORTING"
    #    pass

    dirpath = cfile.dirpath()
    lastdir = path.local()
    os.chdir(str(dirpath))
    try:
        modname = cfile.get('purebasename') 
        if debug: print "modname", modname
        c = stdoutcapture.Capture(mixed_out_err = True)
        try:
            try:
                setup(
                  name = "testmodules",
                  ext_modules=[ 
                        Extension(modname, [str(cfile)])
                  ],
                  script_name = 'setup.py',
                  script_args = ['-q', 'build_ext', '--inplace']
                  #script_args = ['build_ext', '--inplace']
                )
            finally:
                foutput, foutput = c.done()
        except:
            print foutput.read()
            raise
        # XXX do we need to do some check on fout/ferr?
        # XXX not a nice way to import a module
        if debug: print "inserting path to sys.path", dirpath
        sys.path.insert(0, '.')
        if debug: print "import %(modname)s as testmodule" % locals()
        exec "import %(modname)s as testmodule" % locals()
        sys.path.pop(0)
    finally:
        os.chdir(str(lastdir))
        #if not debug:
        #dirpath.rmtree()
    return testmodule

def make_c_from_pyxfile(pyxfile):
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
    space = Space()
    name = func.func_name
    funcgraph = space.build_flow(func)

    if not inputargtypes: 
        source = inspect.getsource(func)
        base = udir.join(name).new(ext='.py').write(source) 

    if dot:
        from pypy.translator.tool.make_dot import DotGen
        dotgen = DotGen()
        subgraphs = []
        subgraphs.append(dotgen.getsubgraph(name, funcgraph))

    # apply transformations 
    if simplify:
        from pypy.translator.simplify import simplify_graph
        simplify_graph(funcgraph)
        name += '_s'

    # get the pyrex generator
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
            subgraphs.append(dotgen.getsubgraph(name, funcgraph))
        content = dotgen.getgraph("graph_"+func.func_name, subgraphs)
        base = udir.join(name)
        base.new(ext='dot').write(content)
        base.new(ext='ps')
        cmdexec('dot -Tps -o %s %s' % (
            str(base.new(ext='ps')),
            str(base.new(ext='.dot'))))

    return getattr(mod, func.func_name)
