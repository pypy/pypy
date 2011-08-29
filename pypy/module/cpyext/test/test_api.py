import py
from pypy.conftest import gettestobjspace
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.interpreter.baseobjspace import W_Root
from pypy.module.cpyext.state import State
from pypy.module.cpyext import api
from pypy.module.cpyext.test.test_cpyext import freeze_refcnts, LeakCheckingTest
PyObject = api.PyObject
from pypy.interpreter.error import OperationError
from pypy.module.cpyext.state import State
import os

@api.cpython_api([PyObject], lltype.Void)
def PyPy_GetWrapped(space, w_arg):
    assert isinstance(w_arg, W_Root)
@api.cpython_api([PyObject], lltype.Void)
def PyPy_GetReference(space, arg):
    assert lltype.typeOf(arg) ==  PyObject

class BaseApiTest(LeakCheckingTest):
    def setup_class(cls):
        cls.space = space = gettestobjspace(usemodules=['cpyext', 'thread', '_rawffi'])

        # warm up reference counts:
        # - the posix module allocates a HCRYPTPROV on Windows
        # - writing to stdout and stderr allocates a file lock
        space.getbuiltinmodule("cpyext")
        space.getbuiltinmodule(os.name)
        space.call_function(space.getattr(space.sys.get("stderr"),
                                          space.wrap("write")),
                            space.wrap(""))
        space.call_function(space.getattr(space.sys.get("stdout"),
                                          space.wrap("write")),
                            space.wrap(""))

        class CAPI:
            def __getattr__(self, name):
                return getattr(cls.space, name)
        cls.api = CAPI()
        CAPI.__dict__.update(api.INTERPLEVEL_API)

    def raises(self, space, api, expected_exc, f, *args):
        if not callable(f):
            raise Exception("%s is not callable" % (f,))
        f(*args)
        state = space.fromcache(State)
        operror = state.operror
        if not operror:
            raise Exception("DID NOT RAISE")
        if getattr(space, 'w_' + expected_exc.__name__) is not operror.w_type:
            raise Exception("Wrong exception")
        state.clear_exception()

    def setup_method(self, func):
        freeze_refcnts(self)

    def teardown_method(self, func):
        state = self.space.fromcache(State)
        try:
            state.check_and_raise_exception()
        except OperationError, e:
            print e.errorstr(self.space)
            raise

        try:
            del self.space.getexecutioncontext().cpyext_threadstate
        except AttributeError:
            pass

        if self.check_and_print_leaks():
            assert False, "Test leaks or loses object(s)."

@api.cpython_api([api.Py_ssize_t], api.Py_ssize_t, error=-1)
def PyPy_TypedefTest1(space, arg):
    assert lltype.typeOf(arg) == api.Py_ssize_t
    return 0

@api.cpython_api([api.Py_ssize_tP], api.Py_ssize_tP)
def PyPy_TypedefTest2(space, arg):
    assert lltype.typeOf(arg) == api.Py_ssize_tP
    return None

class TestConversion(BaseApiTest):
    def test_conversions(self, space, api):
        api.PyPy_GetWrapped(space.w_None)
        api.PyPy_GetReference(space.w_None)

    def test_typedef(self, space):
        from pypy.translator.c.database import LowLevelDatabase
        db = LowLevelDatabase()
        assert (api.c_function_signature(db, api.FUNCTIONS['PyPy_TypedefTest1'])
                == ('Py_ssize_t', 'Py_ssize_t arg0'))
        assert (api.c_function_signature(db, api.FUNCTIONS['PyPy_TypedefTest2'])
                == ('Py_ssize_t *', 'Py_ssize_t *arg0'))

        PyPy_TypedefTest1(space, 0)
        ppos = lltype.malloc(api.Py_ssize_tP.TO, 1, flavor='raw')
        ppos[0] = 0
        PyPy_TypedefTest2(space, ppos)
        lltype.free(ppos, flavor='raw')


def test_copy_header_files(tmpdir):
    api.copy_header_files(tmpdir)
    def check(name):
        f = tmpdir.join(name)
        assert f.check(file=True)
        py.test.raises(py.error.EACCES, "f.open('w')") # check that it's not writable
    check('Python.h')
    check('modsupport.h')
    check('pypy_decl.h')
