import sys
import py
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib import jit
from pypy.jit.backend.x86.test.test_zrpy_gc import compile_and_run

from pypy.jit.metainterp import pyjitpl

#pyjitpl.DEBUG = 4


def test_stack_alignment():
    if sys.platform != 'darwin':
        py.test.skip("tests darwin only stack alignment requirements")
        
    externs = ["""
extern void check0();
extern void check1(int);
extern void check2(int, int);
extern void check3(int, int, int);
"""]
    c_source = r"""
#include <stdio.h>
    
void check0() {
    void *ip = __builtin_return_address(0);
    void *fp = __builtin_frame_address(0);
    printf("0 %p %p %u\n", ip, fp, (unsigned)fp % 16);
}

void check1(int a) {
    void *ip = __builtin_return_address(0);
    void *fp = __builtin_frame_address(0);
    printf("1 %p %p %u\n", ip, fp, (unsigned)fp % 16);
}

void check2(int a, int b) {
    void *ip = __builtin_return_address(0);
    void *fp = __builtin_frame_address(0);
    printf("2 %p %p %u\n", ip, fp, (unsigned)fp % 16);
}

void check3(int a, int b, int c) {
    void *ip = __builtin_return_address(0);
    void *fp = __builtin_frame_address(0);
    printf("3 %p %p %u\n", ip, fp, (unsigned)fp % 16);
}
"""
    
    eci = rffi.ExternalCompilationInfo(separate_module_sources=[c_source],
                  post_include_bits = externs,
                  # not ideal, would like to apply this only to the checkX
                  # functions
                  compile_extra=["-fno-omit-frame-pointer"])

    check0 = rffi.llexternal('check0', [], lltype.Void,
                             compilation_info=eci,
                             _nowrapper=True)
    check1 = rffi.llexternal('check1', [lltype.Signed], lltype.Void,
                             compilation_info=eci,
                             _nowrapper=True)
    check2 = rffi.llexternal('check2', [lltype.Signed, lltype.Signed],
                             lltype.Void,
                             compilation_info=eci,
                             _nowrapper=True)
    
    check3 = rffi.llexternal('check3', [lltype.Signed, lltype.Signed,
                                        lltype.Signed],
                             lltype.Void,
                             compilation_info=eci,
                             _nowrapper=True)            
    
    myjitdriver = jit.JitDriver(greens = [], reds = ['n'])

    def entrypoint(argv):
        myjitdriver.set_param('threshold', 2)
        myjitdriver.set_param('trace_eagerness', 0)
        n = 16
        while n > 0:
            myjitdriver.can_enter_jit(n=n)
            myjitdriver.jit_merge_point(n=n)
            n -= 1
            check0()
            check1(0)
            check2(0, 1)
            check3(0, 1, 2)
        return 0

    output = compile_and_run(entrypoint, 'boehm', jit=True)
    for line in output.splitlines():
        print line
        # ret ip + bp == 8
        assert int(line.split()[-1]) == 8

