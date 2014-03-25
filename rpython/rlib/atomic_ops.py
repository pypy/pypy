import py
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo

eci = ExternalCompilationInfo(
    post_include_bits = ['''
#define pypy_bool_cas(ptr, old, _new)                \\
    __sync_bool_compare_and_swap((volatile unsigned long*)(ptr),  \\
                    (unsigned long)(old),            \\
                    (unsigned long)(_new))
#define pypy_fetch_and_add(ptr, value)                    \\
    __sync_fetch_and_add((volatile unsigned long*)(ptr),  \\
                         (unsigned long)(value))
'''],
)


bool_cas = rffi.llexternal('pypy_bool_cas', [llmemory.Address]*3, lltype.Bool,
                           compilation_info=eci, macro=True, _nowrapper=True,
                           transactionsafe=True)
fetch_and_add = rffi.llexternal('pypy_fetch_and_add', [llmemory.Address,
                                                       lltype.Signed],
                                lltype.Signed, compilation_info=eci,
                                macro=True, _nowrapper=True,
                                transactionsafe=True)
