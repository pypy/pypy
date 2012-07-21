from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.tool import rffi_platform
from pypy.translator.platform import CompilationError

class Exec(rffi_platform.CConfigEntry):
    """An entry in a CConfig class that stands for an integer result of a call.
    """
    def __init__(self, call):
        self.call = call

    def prepare_code(self):
        yield 'long int result = %s;' % (self.call,)
        yield 'if ((result) <= 0) {'
        yield '    long long x = (long long)(result);'
        yield '    printf("value: %lld\\n", x);'
        yield '} else {'
        yield '    unsigned long long x = (unsigned long long)(result);'
        yield '    printf("value: %llu\\n", x);'
        yield '}'

    def build_result(self, info, config_result):
        return rffi_platform.expose_value_as_rpython(info['value'])


hard_float_check = """
// HACK HACK HACK 
// We need to make sure we do not optimize too much of the code
// below we need that check is called in the original version without constant
// propagation or anything that could affect the order and number of the
// arguments passed to it
// For the same reason we call pypy__arm_hard_float_check using a function
// pointer instead of calling it directly

int pypy__arm_hard_float_check(int a, float b, int c) __attribute__((optimize("O0")));
long int pypy__arm_is_hf(void) __attribute__((optimize("O0")));

int pypy__arm_hard_float_check(int a, float b, int c)
{
    int reg_value;
    // get the value that is in the second GPR when we enter the call
    asm volatile("mov    %[result], r1"
    : [result]"=l" (reg_value) : : );
    assert(a == 1);
    assert(b == 2.0);
    assert(c == 3);
    /* if reg_value is 3, then we are using hard
    floats, because the third argument to this call was stored in the
    second core register;*/
    return reg_value == 3;
}

long int pypy__arm_is_hf(void)
{
    int (*f)(int, float, int);
    // trash argument registers, just in case
    asm volatile("movw r0, #65535\\n\\t"
    "movw r1, #65535\\n\\t"
    "movw r2, #65535\\n\\t");
    f = &pypy__arm_hard_float_check;
    return f(1, 2.0, 3);
}
        """
class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes=['assert.h'],
        post_include_bits=[hard_float_check])

    hard_float = Exec('pypy__arm_is_hf()')


eci = ExternalCompilationInfo(
    post_include_bits=["""
// we need to disable optimizations so the compiler does not remove this
// function when checking if the file compiles
static void __attribute__((optimize("O0"))) pypy__arm_has_vfp()
{
    asm volatile("VMOV s0, s1");
}
    """])

hard_float = rffi_platform.configure(CConfig)['hard_float']

def detect_hardfloat():
    return hard_float

def detect_float():
    """Check for hardware float support
    we try to compile a function containing a VFP instruction, and if the
    compiler accepts it we assume we are fine
    """
    try:
        rffi_platform.verify_eci(eci)
        return True
    except CompilationError:
        return False
