extdeclarations =  """;rpython stuff

;gc-type dependent mallocs
declare fastcc sbyte* %gc_malloc(uint)
declare fastcc sbyte* %gc_malloc_atomic(uint)

;exception handling globals
%last_exception_type  = global %RPYTHON_EXCEPTION_VTABLE* null
%last_exception_value = global %RPYTHON_EXCEPTION* null
"""

gc_boehm = """declare ccc sbyte* %GC_malloc(uint)
declare ccc sbyte* %GC_malloc_atomic(uint)
declare ccc sbyte* %memset(sbyte*, int, uint)

internal fastcc sbyte* %gc_malloc(uint %n) {
    %nn = add uint %n, 1
    %ptr = call ccc sbyte* %GC_malloc(uint %nn)
    call ccc sbyte* %memset(sbyte* %ptr, int 0, uint %nn)    ;XXX force non-zero init for testing
    ret sbyte* %ptr
}

internal fastcc sbyte* %gc_malloc_atomic(uint %n) {
    %nn = add uint %n, 1
    %ptr = call ccc sbyte* %GC_malloc_atomic(uint %nn)
    call ccc sbyte* %memset(sbyte* %ptr, int 0, uint %nn)    ;XXX force non-zero init for testing
    ret sbyte* %ptr
}
"""

gc_disabled = """internal fastcc sbyte* %gc_malloc(uint %n) {
    %ptr = malloc sbyte, uint %n
    ret sbyte* %ptr
}

internal fastcc sbyte* %gc_malloc_atomic(uint %n) {
    %ptr = malloc sbyte, uint %n
    ret sbyte* %ptr
}
"""

extfunctions = {}   #dependencies, llvm-code

import support, ll_os, ll_os_path, ll_time, ll_math, ll_strtod

for module in (support, ll_os, ll_os_path, ll_time, ll_math, ll_strtod):
    extdeclarations += module.extdeclarations
    extfunctions.update(module.extfunctions)
extdeclarations += '\n;application function prototypes'

def dependencies(funcname, deplist):
    deplist.append(funcname)
    if funcname in extfunctions:
        for depfuncname in extfunctions[funcname][0]:
            if depfuncname not in deplist:  #avoid loops
                dependencies(depfuncname, deplist)
    return deplist
