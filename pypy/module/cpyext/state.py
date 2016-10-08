from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.executioncontext import AsyncAction
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.annlowlevel import llhelper
from rpython.rlib.rdynload import DLLHANDLE
from rpython.rlib import rawrefcount
import sys

class State:
    def __init__(self, space):
        self.space = space
        self.reset()
        self.programname = lltype.nullptr(rffi.CWCHARP.TO)
        self.version = lltype.nullptr(rffi.CCHARP.TO)
        pyobj_dealloc_action = PyObjDeallocAction(space)
        self.dealloc_trigger = lambda: pyobj_dealloc_action.fire()

    def reset(self):
        from pypy.module.cpyext.modsupport import PyMethodDef
        self.operror = None
        self.new_method_def = lltype.nullptr(PyMethodDef)

        # When importing a package, use this to keep track
        # of its name and path (as a 2-tuple).  This is
        # necessary because an extension module in a package might not supply
        # its own fully qualified name to Py_InitModule.  If it doesn't, we need
        # to be able to figure out what module is being initialized.  Recursive
        # imports will clobber this value, which might be confusing, but it
        # doesn't hurt anything because the code that cares about it will have
        # already read it by that time.
        self.package_context = None, None

        # A mapping {filename: copy-of-the-w_dict}, similar to CPython's
        # variable 'extensions' in Python/import.c.
        self.extensions = {}

    def set_exception(self, operror):
        self.clear_exception()
        self.operror = operror

    def clear_exception(self):
        """Clear the current exception state, and return the operror."""
        operror = self.operror
        self.operror = None
        return operror

    def check_and_raise_exception(self, always=False):
        operror = self.operror
        if operror:
            self.clear_exception()
            raise operror
        if always:
            raise oefmt(self.space.w_SystemError,
                        "Function returned an error result without setting an "
                        "exception")

    def build_api(self, space):
        """NOT_RPYTHON
        This function is called when at object space creation,
        and drives the compilation of the cpyext library
        """
        from pypy.module.cpyext import api
        state = self.space.fromcache(State)
        if not self.space.config.translating:
            state.api_lib = str(api.build_bridge(self.space))
        else:
            api.setup_library(self.space)

    def install_dll(self, eci):
        """NOT_RPYTHON
        Called when the dll has been compiled"""
        if sys.platform == 'win32':
            self.get_pythonapi_handle = rffi.llexternal(
                'pypy_get_pythonapi_handle', [], DLLHANDLE,
                compilation_info=eci)

    def startup(self, space):
        "This function is called when the program really starts"

        from pypy.module.cpyext.typeobject import setup_new_method_def
        from pypy.module.cpyext.api import INIT_FUNCTIONS
        from pypy.module.cpyext.api import init_static_data_translated

        if we_are_translated():
            rawrefcount.init(llhelper(rawrefcount.RAWREFCOUNT_DEALLOC_TRIGGER,
                                      self.dealloc_trigger))
            init_static_data_translated(space)

        setup_new_method_def(space)

        for func in INIT_FUNCTIONS:
            func(space)
            self.check_and_raise_exception()

    def get_programname(self):
        if not self.programname:
            space = self.space
            argv = space.sys.get('argv')
            if space.len_w(argv):
                argv0 = space.getitem(argv, space.wrap(0))
                progname = space.unicode_w(argv0)
            else:
                progname = u"pypy"
            self.programname = rffi.unicode2wcharp(progname)
            lltype.render_immortal(self.programname)
        return self.programname

    def get_version(self):
        if not self.version:
            space = self.space
            w_version = space.sys.get('version')
            version = space.str_w(w_version)
            self.version = rffi.str2charp(version)
            lltype.render_immortal(self.version)
        return self.version
        foo = self.import_module(name='foo', init=init)

    def find_extension(self, name, path):
        from pypy.module.cpyext.import_ import PyImport_AddModule
        from pypy.interpreter.module import Module
        try:
            w_dict = self.extensions[path]
        except KeyError:
            return None
        with rffi.scoped_str2charp(name) as ll_name:
            w_mod = PyImport_AddModule(self.space, ll_name)
        assert isinstance(w_mod, Module)
        w_mdict = w_mod.getdict(self.space)
        self.space.call_method(w_mdict, 'update', w_dict)
        return w_mod

    def fixup_extension(self, w_mod, name, path):
        from pypy.interpreter.module import Module
        space = self.space
        w_modules = space.sys.get('modules')
        space.setitem_str(w_modules, name, w_mod)
        w_dict = w_mod.getdict(space)
        w_copy = space.call_method(w_dict, 'copy')
        self.extensions[path] = w_copy


class PyObjDeallocAction(AsyncAction):
    """An action that invokes _Py_Dealloc() on the dying PyObjects.
    """

    def perform(self, executioncontext, frame):
        from pypy.module.cpyext.pyobject import PyObject, decref

        while True:
            py_obj = rawrefcount.next_dead(PyObject)
            if not py_obj:
                break
            decref(self.space, py_obj)
