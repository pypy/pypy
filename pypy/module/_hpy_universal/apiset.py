import re
from rpython.rtyper.annlowlevel import llhelper
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.tool.sourcetools import func_with_new_name
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.objectmodel import specialize, llhelper_can_raise
from pypy.module._hpy_universal import llapi

class APISet(object):

    def __init__(self, cts, prefix=r'^_?HPy_?', force_c_name=False):
        self.cts = cts
        self.prefix = re.compile(prefix)
        self.force_c_name = force_c_name
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

    def func(self, cdecl, cpyext=False, func_name=None):
        """
        Declare an HPy API function.

        If the function is marked as cpyext=True, it will be included in the
        translation only if pypy.objspace.hpy_cpyext_API==True (the
        default). This is useful to exclude cpyext in test_ztranslation

        If func_name is given, the decorated function will be automatically
        renamed. Useful for automatically generated code, for example in
        interp_number.py
        """
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
            if func_name is not None:
                fn = func_with_new_name(fn, func_name)
            #
            # attach various helpers to fn, so you can access things like
            # HPyNumber_Add.get_llhelper(), HPyNumber_Add.basename, etc.

            # get_llhelper
            @specialize.memo()
            def make_wrapper(space):
                @llhelper_can_raise
                def wrapper(*args):
                    return fn(space, *args)
                wrapper.__name__ = 'ctx_%s' % fn.__name__
                if self.force_c_name:
                    wrapper.c_name = fn.__name__
                return wrapper
            def get_llhelper(space):
                return llhelper(ll_functype, make_wrapper(space))
            get_llhelper.__name__ = 'get_llhelper_%s' % fn.__name__
            fn.get_llhelper = get_llhelper

            # basename
            fn.basename = self.prefix.sub(r'', fn.__name__)

            fn.cpyext = cpyext
            # record it into the API
            self.all_functions.append(fn)
            return fn
        return decorate

    @staticmethod
    def int(x):
        """
        Helper method to convert an RPython Signed into a C int
        """
        return rffi.cast(rffi.INT_real, x)

    @staticmethod
    def ccharp2text(space, ptr):
        """
        Convert a C const char* into a W_UnicodeObject
        """
        s = rffi.constcharp2str(ptr)
        return space.newtext(s)



API = APISet(llapi.cts)
