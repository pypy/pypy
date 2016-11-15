from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rtyper.lltypesystem import lltype

def ll_assert(x, msg):
    """After translation to C, this becomes an RPyAssert."""
    assert type(x) is bool, "bad type! got %r" % (type(x),)
    assert x, msg

class Entry(ExtRegistryEntry):
    _about_ = ll_assert

    def compute_result_annotation(self, s_x, s_msg):
        assert s_msg.is_constant(), ("ll_assert(x, msg): "
                                     "the msg must be constant")
        return None

    def specialize_call(self, hop):
        vlist = hop.inputargs(lltype.Bool, lltype.Void)
        hop.exception_cannot_occur()
        hop.genop('debug_assert', vlist)

class FatalError(Exception):
    pass

def fatalerror(msg):
    # print the RPython traceback and abort with a fatal error
    if not we_are_translated():
        raise FatalError(msg)
    from rpython.rtyper.lltypesystem import lltype
    from rpython.rtyper.lltypesystem.lloperation import llop
    llop.debug_print_traceback(lltype.Void)
    llop.debug_fatalerror(lltype.Void, msg)
fatalerror._dont_inline_ = True
fatalerror._jit_look_inside_ = False
fatalerror._annenforceargs_ = [str]

def fatalerror_notb(msg):
    # a variant of fatalerror() that doesn't print the RPython traceback
    if not we_are_translated():
        raise FatalError(msg)
    from rpython.rtyper.lltypesystem import lltype
    from rpython.rtyper.lltypesystem.lloperation import llop
    llop.debug_fatalerror(lltype.Void, msg)
fatalerror_notb._dont_inline_ = True
fatalerror_notb._jit_look_inside_ = False
fatalerror_notb._annenforceargs_ = [str]

def debug_print_traceback():
    # print to stderr the RPython traceback of the last caught exception,
    # but without interrupting the program
    from rpython.rtyper.lltypesystem import lltype
    from rpython.rtyper.lltypesystem.lloperation import llop
    llop.debug_print_traceback(lltype.Void)
debug_print_traceback._dont_inline_ = True
debug_print_traceback._jit_look_inside_ = False
