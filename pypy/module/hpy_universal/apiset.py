import re
from rpython.rtyper.annlowlevel import llhelper
from rpython.rtyper.lltypesystem import lltype
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.objectmodel import specialize, llhelper_can_raise


class APISet(object):

    _PREFIX = re.compile(r'^_?HPy_?')

    def __init__(self):
        self.all_functions = []

    def _freeze_(self):
        self.all_functions = unrolling_iterable(self.all_functions)
        return True

    def func(self, argtypes, restype):
        def decorate(fn):
            # attach various helpers to fn, so you can access things like
            # HPyNumber_Add.get_llhelper(), HPyNumber_Add.basename, etc.

            # get_llhelper
            ll_functype = lltype.Ptr(lltype.FuncType(argtypes, restype))
            @specialize.memo()
            def make_wrapper(space):
                @llhelper_can_raise
                def wrapper(*args):
                    return fn(space, *args)
                return wrapper
            def get_llhelper(space):
                return llhelper(ll_functype, make_wrapper(space))
            fn.get_llhelper = get_llhelper

            # basename
            fn.basename = self._PREFIX.sub(r'', fn.__name__)

            # record it into the API
            self.all_functions.append(fn)
            return fn
        return decorate

API = APISet()
