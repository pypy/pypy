
import autopath
from pypy.tool import test

from vpath.local import Path, mkdtemp
import os, sys

def make_module_from_pyxstring(string, num=[0]):
    tmpdir = mkdtemp()
    n = num[0] = num[0]+1
    pyxfile = tmpdir.join('test%d.pyx' %n) 
    pyxfile.write(string)
    print "made pyxfile", pyxfile
    make_c_from_pyxfile(pyxfile)
    module = make_module_from_c(pyxfile)
    #print "made module", module
    return module

def make_module_from_c(pyxfile):
    from distutils.core import setup
    from distutils.extension import Extension
    from Pyrex.Distutils import build_ext

    dirpath = pyxfile.dirname()
    lastdir = os.curdir
    os.chdir(str(dirpath))
    try:
        modname = pyxfile.purebasename()
        print "modname", modname
        setup(
          name = "testmodules",
          ext_modules=[ 
                Extension(modname, [str(pyxfile)])
          ],
          cmdclass = {'build_ext': build_ext},
          script_name = 'setup.py',
          script_args = ['build_ext', '--inplace', '-q'] # , '--quiet']
        )
        # XXX not a nice way to import a module
        print "inserting path to sys.path", dirpath
        sys.path.insert(0, '.')
        print "import %(modname)s as testmodule" % locals()
        exec "import %(modname)s as testmodule" % locals()
        sys.path.pop(0)
    finally:
        os.chdir(lastdir)
        #dirpath.rmtree()
    return testmodule

def make_c_from_pyxfile(pyxfile):
    from Pyrex.Compiler.Main import CompilationOptions, Context, PyrexError
    try:
        options = CompilationOptions(show_version = 0, 
                                     use_listing_file = 0, 
                                     output_file = None)
        context = Context(options.include_path)
        result = context.compile(str(pyxfile), options, c_only = 1)
        if result.num_errors > 0:
            raise ValueError, "failure %s" % result
    except PyrexError, e:
        print >>sys.stderr, e
    cfile = pyxfile.newsuffix('.c')
