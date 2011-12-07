from pypy.interpreter.baseobjspace import W_Root, ObjSpace
from pypy.translator.driver import TranslationDriver
from pypy.annotation.model import SomeInstance, s_None
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import lltype


def is_root(w_obj):
    assert isinstance(w_obj, W_Root)

class Entry(ExtRegistryEntry):
    _about_ = is_root

    def compute_result_annotation(self, s_w_obj):
        s_inst = SomeInstance(self.bookkeeper.getuniqueclassdef(W_Root))
        assert s_inst.contains(s_w_obj)
        return s_None

    def specialize_call(self, hop):
        return hop.inputconst(lltype.Void, None)

# ____________________________________________________________


class FakeObjSpace(ObjSpace):

    def translates(self, func, argtypes=None):
        if argtypes is None:
            nb_args = func.func_code.co_argcount
            argtypes = [W_Root] * nb_args
        #
        driver = TranslationDriver()
        driver.setup(func, argtypes)
        driver.proceed(['rtype_lltype'])

    def add(self, w_x, w_y):
        is_root(w_x)
        is_root(w_y)
        return W_Root()
