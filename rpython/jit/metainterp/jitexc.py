from rpython.rtyper.annlowlevel import cast_instance_to_base_ptr
from rpython.rtyper.annlowlevel import cast_base_ptr_to_instance
from rpython.rtyper.lltypesystem import rclass
from rpython.rtyper.llinterp import LLException
from rpython.rlib.objectmodel import we_are_translated


class JitException(Exception):
    """The base class for exceptions raised and caught in the JIT.
    The point is that the places that catch any user exception should avoid
    catching exceptions that inherit from JitException.
    """
    _go_through_llinterp_uncaught_ = True     # ugh

def _get_standard_error(rtyper, Class):
    exdata = rtyper.getexceptiondata()
    clsdef = rtyper.annotator.bookkeeper.getuniqueclassdef(Class)
    evalue = exdata.get_standard_ll_exc_instance(rtyper, clsdef)
    return evalue

def get_llexception(cpu, e):
    if we_are_translated():
        return cast_instance_to_base_ptr(e)
    assert not isinstance(e, JitException)
    if isinstance(e, LLException):
        return e.args[1]    # ok
    if isinstance(e, OverflowError):
        return _get_standard_error(cpu.rtyper, OverflowError)
    raise   # leave other exceptions to be propagated

def reraise(lle):
    if we_are_translated():
        e = cast_base_ptr_to_instance(Exception, lle)
        raise e
    else:
        etype = rclass.ll_type(lle)
        raise LLException(etype, lle)
