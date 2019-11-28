import re
from rpython.rtyper.annlowlevel import llhelper
from rpython.rtyper.lltypesystem import lltype
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.objectmodel import specialize, llhelper_can_raise
from pypy.module.hpy_universal import llapi

class APISet(object):

    _PREFIX = re.compile(r'^_?HPy_?')

    def __init__(self, cts):
        self.cts = cts
        self.all_functions = []
        self.frozen = False

    def _freeze_(self):
        self.all_functions = unrolling_iterable(self.all_functions)
        self.frozen = True
        return True

    def parse_signature(self, cdecl):
        d = self.cts.parse_func(cdecl)
        argtypes = d.get_llargs(self.cts)
        restype = d.get_llresult(self.cts)
        ll_functype = lltype.Ptr(lltype.FuncType(argtypes, restype))
        return d.name, ll_functype

    def func(self, cdecl):
        if self.frozen:
            raise RuntimeError(
                'Too late to call @api.func(), the API object has already been frozen. '
                'If you are calling @api.func() to decorate module-level functions, '
                'you might solve this by making sure that the module is imported '
                'earlier')
        def decorate(fn):
            name, ll_functype = self.parse_signature(cdecl)
            if name != fn.__name__:
                raise ValueError(
                    'The name of the function and the signature do not match: '
                    '%s != %s' % (name, fn.__name__))
            #
            # attach various helpers to fn, so you can access things like
            # HPyNumber_Add.get_llhelper(), HPyNumber_Add.basename, etc.

            # get_llhelper
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

API = APISet(llapi.cts)
