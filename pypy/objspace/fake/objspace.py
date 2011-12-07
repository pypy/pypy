from pypy.interpreter.baseobjspace import W_Root, ObjSpace
from pypy.interpreter import argument
from pypy.translator.driver import TranslationDriver
from pypy.annotation.model import SomeInstance, s_None
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import lltype
from pypy.tool.sourcetools import compile2, func_with_new_name
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import we_are_translated


def is_root(w_obj):
    assert isinstance(w_obj, W_Root)
is_root.expecting = W_Root

def is_arguments(arg):
    assert isinstance(arg, argument.Arguments)
is_arguments.expecting = argument.Arguments


class Entry(ExtRegistryEntry):
    _about_ = is_root, is_arguments

    def compute_result_annotation(self, s_w_obj):
        cls = self.instance.expecting
        s_inst = SomeInstance(self.bookkeeper.getuniqueclassdef(cls),
                              can_be_None=True)
        assert s_inst.contains(s_w_obj)
        return s_None

    def specialize_call(self, hop):
        return hop.inputconst(lltype.Void, None)

# ____________________________________________________________


class FakeObjSpace(ObjSpace):

    def __init__(self):
        self.seen_wrap = []
        ObjSpace.__init__(self)

    w_None = W_Root()
    w_False = W_Root()
    w_True = W_Root()

    def newdict(self, module=False, instance=False, classofinstance=None,
                strdict=False):
        return W_Root()

    def wrap(self, x):
        if not we_are_translated():
            self.seen_wrap.append(x)
        return W_Root()
    wrap._annspecialcase_ = "specialize:argtype(1)"

    def call_args(self, w_func, args):
        is_root(w_func)
        is_arguments(args)
        return W_Root()

    def gettypefor(self, cls):
        assert issubclass(cls, W_Root)
        return W_Root()

    # ----------

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
