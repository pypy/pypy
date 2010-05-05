from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.lib.identity_dict import identity_dict
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import lltype


class State:
    def __init__(self, space):
        self.space = space
        self.reset()

    def reset(self):
        from pypy.module.cpyext.modsupport import PyMethodDef
        self.py_objects_w2r = {} # { w_obj -> raw PyObject }
        self.py_objects_r2w = {} # { addr of raw PyObject -> w_obj }
        self.borrow_mapping = {} # { addr of container -> { addr of containee -> None } }
        self.borrowed_objects = {} # { addr of containee -> None }
        self.non_heaptypes = [] # list of wrapped objects
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


    def _freeze_(self):
        assert not self.borrowed_objects and not self.borrow_mapping
        self.py_objects_r2w.clear() # is not valid anymore after translation
        return False

    def init_r2w_from_w2r(self):
        from pypy.module.cpyext.api import ADDR
        for w_obj, obj in self.py_objects_w2r.items():
            ptr = rffi.cast(ADDR, obj)
            self.py_objects_r2w[ptr] = w_obj

    def set_exception(self, operror):
        self.clear_exception()
        self.operror = operror

    def clear_exception(self):
        """Clear the current exception state, and return the operror.
        Also frees the borrowed reference returned by PyErr_Occurred()
        """
        from pypy.module.cpyext.pyobject import Py_DecRef, make_ref
        from pypy.module.cpyext.api import ADDR
        # handling of borrowed objects, remove when we have
        # a weakkeydict
        operror = self.operror
        if operror is not None:
            exc_type = make_ref(self.space, operror.w_type, borrowed=True)
            Py_DecRef(self.space, exc_type)
            containee_ptr = rffi.cast(ADDR, exc_type)
            del self.borrowed_objects[containee_ptr]
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

    def print_refcounts(self):
        print "REFCOUNTS"
        for w_obj, obj in self.py_objects_w2r.items():
            print "%r: %i" % (w_obj, obj.c_ob_refcnt)
