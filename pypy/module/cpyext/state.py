from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import lltype


class State:
    def __init__(self, space):
        self.space = space
        self.reset()
        self.programname = lltype.nullptr(rffi.CCHARP.TO)

    def reset(self):
        from pypy.module.cpyext.modsupport import PyMethodDef
        self.operror = None
        self.new_method_def = lltype.nullptr(PyMethodDef)

        # When importing a package, use this to keep track of its name.  This is
        # necessary because an extension module in a package might not supply
        # its own fully qualified name to Py_InitModule.  If it doesn't, we need
        # to be able to figure out what module is being initialized.  Recursive
        # imports will clobber this value, which might be confusing, but it
        # doesn't hurt anything because the code that cares about it will have
        # already read it by that time.
        self.package_context = None

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
            raise OperationError(self.space.w_SystemError, self.space.wrap(
                "Function returned an error result without setting an exception"))

    def get_programname(self):
        if not self.programname:
            space = self.space
            argv = space.sys.get('argv')
            if space.int_w(space.len(argv)):
                argv0 = space.getitem(argv, space.wrap(0))
                progname = space.str_w(argv0)
            else:
                progname = "pypy"
            self.programname = rffi.str2charp(progname)
            lltype.render_immortal(self.programname)
        return self.programname
