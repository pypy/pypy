from pypy.interpreter.baseobjspace import W_Root, ObjSpace
from pypy.translator.driver import TranslationDriver
from pypy.annotation.model import SomeInstance, s_None
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import lltype
from pypy.tool.sourcetools import compile2, func_with_new_name


def is_root(w_obj):
    assert isinstance(w_obj, W_Root)

class Entry(ExtRegistryEntry):
    _about_ = is_root

    def compute_result_annotation(self, s_w_obj):
        s_inst = SomeInstance(self.bookkeeper.getuniqueclassdef(W_Root),
                              can_be_None=True)
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


def setup():
    for (name, _, arity, _) in ObjSpace.MethodTable:
        args = ['w_%d' % i for i in range(arity)]
        d = {'is_root': is_root,
             'W_Root': W_Root}
        exec compile2("""\
            def meth(self, %s):
                %s
                return W_Root()
        """ % (', '.join(args),
               '; '.join(['is_root(%s)' % arg for arg in args]))) in d
        meth = func_with_new_name(d['meth'], name)
        setattr(FakeObjSpace, name, meth)

setup()
