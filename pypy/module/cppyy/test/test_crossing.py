import py, os, sys

from pypy.interpreter.gateway import interp2app, unwrap_spec
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.translator import platform
from rpython.translator.gensupp import uniquemodulename
from rpython.tool.udir import udir

from pypy.module.cpyext import api
from pypy.module.cpyext.state import State

from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


currpath = py.path.local(__file__).dirpath()
test_dct = str(currpath.join("crossingDict.so"))

def setup_module(mod):
    if sys.platform == 'win32':
        py.test.skip("win32 not supported so far")
    err = os.system("cd '%s' && make crossingDict.so" % currpath)
    if err:
        raise OSError("'make' failed (see stderr)")

# from pypy/module/cpyext/test/test_cpyext.py; modified to accept more external
# symbols and called directly instead of import_module
def compile_extension_module(space, modname, symbols, **kwds):
    """
    Build an extension module and return the filename of the resulting native
    code file.

    modname is the name of the module, possibly including dots if it is a module
    inside a package.

    Any extra keyword arguments are passed on to ExternalCompilationInfo to
    build the module (so specify your source with one of those).
    """
    state = space.fromcache(State)
    api_library = state.api_lib
    if sys.platform == 'win32':
        kwds["libraries"] = [api_library]
        # '%s' undefined; assuming extern returning int
        kwds["compile_extra"] = ["/we4013"]
    elif sys.platform == 'darwin':
        kwds["link_files"] = [str(api_library + '.dylib')]
    else:
        kwds["link_files"] = [str(api_library + '.so')]
        if sys.platform.startswith('linux'):
            kwds["compile_extra"]=["-Werror=implicit-function-declaration"]

    modname = modname.split('.')[-1]
    eci = ExternalCompilationInfo(
        #export_symbols=['init%s' % (modname,)]+symbols,
        include_dirs=api.include_dirs,
        **kwds
        )
    eci = eci.convert_sources_to_files()
    dirname = (udir/uniquemodulename('module')).ensure(dir=1)
    soname = platform.platform.compile(
        [], eci,
        outputfilename=str(dirname/modname),
        standalone=False)
    from pypy.module.imp.importing import get_so_extension
    pydname = soname.new(purebasename=modname, ext=get_so_extension(space))
    soname.rename(pydname)
    return str(pydname)

class AppTestCrossing(AppTestCpythonExtensionBase):
    spaceconfig = dict(usemodules=['cppyy', '_rawffi', 'itertools', 'cpyext'])

    def setup_class(cls):
        AppTestCpythonExtensionBase.setup_class.im_func(cls)
        # cppyy specific additions (note that test_dct is loaded late
        # to allow the generated extension module be loaded first)
        cls.w_test_dct    = cls.space.wrap(test_dct)
        cls.w_pre_imports = cls.space.appexec([], """():
            import cppyy, cpyext, ctypes""")    # prevents leak-checking complaints on ctypes

    def setup_method(self, func):
        AppTestCpythonExtensionBase.setup_method.im_func(self, func)

        @unwrap_spec(name=str, init=str, body=str)
        def create_cdll(space, name, init, body, w_symbols):
            # the following is loosely from test_cpyext.py import_module; it
            # is copied here to be able to tweak the call to
            # compile_extension_module and to get a different return result
            # than in that function
            code = """
            #include <Python.h>
            %(body)s

            PyMODINIT_FUNC
            init%(name)s(void) {
            %(init)s
            }
            """ % dict(name=name, init=init, body=body)
            kwds = dict(separate_module_sources=[code])
            symbols = [space.str_w(w_item) for w_item in space.fixedview(w_symbols)]
            mod = compile_extension_module(space, name, symbols, **kwds)

            # explicitly load the module as a CDLL rather than as a module
            from pypy.module.imp.importing import get_so_extension
            fullmodname = os.path.join(
                os.path.dirname(mod), name + get_so_extension(space))
            return space.wrap(fullmodname)

        self.w_create_cdll = self.space.wrap(interp2app(create_cdll))

    def test00_base_class(self):
        """Test from cpyext; only here to see whether the imported class works"""

        import sys
        init = """
        if (Py_IsInitialized())
            Py_InitModule("foo", NULL);
        """
        self.import_module(name='foo', init=init)
        assert 'foo' in sys.modules

    def test01_build_bar_extension(self):
        """Test that builds the needed extension; runs as test to keep it loaded"""

        import os, ctypes

        name = 'bar'

        init = """
        if (Py_IsInitialized())
            Py_InitModule("bar", methods);
        """

        # note: only the symbols are needed for C, none for python
        body = """
        long bar_unwrap(PyObject* arg)
        {
            return PyLong_AsLong(arg);
        }
        PyObject* bar_wrap(long l)
        {
            return PyLong_FromLong(l);
        }
        static PyMethodDef methods[] = {
            { NULL }
        };
        """
        # explicitly load the module as a CDLL rather than as a module
        import ctypes
        self.cmodule = ctypes.CDLL(
            self.create_cdll(name, init, body, ['bar_unwrap', 'bar_wrap']),
            ctypes.RTLD_GLOBAL)

    def test02_crossing_dict(self):
        """Test availability of all needed classes in the dict"""

        import cppyy
        cppyy.load_reflection_info(self.test_dct)

        assert cppyy.gbl.crossing == cppyy.gbl.crossing
        crossing = cppyy.gbl.crossing

        assert crossing.A == crossing.A

    def test03_send_pyobject(self):
        """Test sending a true pyobject to C++"""

        import cppyy
        crossing = cppyy.gbl.crossing

        a = crossing.A()
        assert a.unwrap(13) == 13

    def test04_send_and_receive_pyobject(self):
        """Test receiving a true pyobject from C++"""

        import cppyy
        crossing = cppyy.gbl.crossing

        a = crossing.A()

        assert a.wrap(41) == 41
