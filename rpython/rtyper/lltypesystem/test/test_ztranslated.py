import sys
import gc
from rpython.translator.c.test.test_genc import compile
from rpython.rtyper.lltypesystem import rffi
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.annlowlevel import llstr, hlstr
from rpython.rtyper.lltypesystem.lloperation import llop

def setup_module(mod):
    pass

def debug_assert(boolresult, msg):
    if not boolresult:
        llop.debug_print(lltype.Void, "\n\nassert failed: %s\n\n" % msg)
        assert boolresult

def use_str():
    mystr = b'abc'[:]
    ptr = rffi.get_raw_address_of_string(mystr)
    ptr2 = rffi.get_raw_address_of_string(mystr)
    debug_assert(ptr == ptr2, "ptr != ptr2")
    debug_assert(ptr[0] == b'a', "notnurseryadr[0] == b'a' is is %s" % ptr[0])
    ptr[0] = b'x' # oh no no, in real programs nobody is allowed to modify that
    debug_assert(mystr[0] in b'ax', "mystr[0] in b'ax'")
    debug_assert(ptr[0] == b'x', "notnurseryadr[0] == b'x'")
    gc.collect()
    nptr = rffi.get_raw_address_of_string(mystr)
    debug_assert(nptr == ptr, "second call to mystr must return the same ptr")
    debug_assert(ptr[0] == b'x', "failure a")
    debug_assert(nptr[0] == b'x', "failure b")
    mystr = None

def main(argv=[]):
    use_str()
    llop.debug_print(lltype.Void, "passed first call to use_str")
    gc.collect()
    return 0

# ____________________________________________________________

def target(driver, args):
    return main

def test_compiled():
    fn = compile(main, [], gcpolicy="minimark")
    fn()
