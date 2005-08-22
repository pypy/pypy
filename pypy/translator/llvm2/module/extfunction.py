extdeclarations =  """;rpython stuff

;gc-type dependent mallocs
declare fastcc sbyte* %gc_malloc(UINT)
declare fastcc sbyte* %gc_malloc_atomic(UINT)

;exception handling globals
%last_exception_type  = global %RPYTHON_EXCEPTION_VTABLE* null
%last_exception_value = global %RPYTHON_EXCEPTION* null
"""

gc_boehm = """declare ccc sbyte* %GC_malloc(UINT)
declare ccc sbyte* %GC_malloc_atomic(UINT)

internal fastcc sbyte* %gc_malloc(UINT %n) {
    %ptr = call ccc sbyte* %GC_malloc(UINT %n)
    ret sbyte* %ptr
}

internal fastcc sbyte* %gc_malloc_atomic(UINT %n) {
    %ptr = call ccc sbyte* %GC_malloc_atomic(UINT %n)
    ret sbyte* %ptr
}
"""

gc_disabled = """internal fastcc sbyte* %gc_malloc(UINT %n) {
    %nn  = cast UINT %n to uint
    %ptr = malloc sbyte, uint %nn
    ret sbyte* %ptr
}

internal fastcc sbyte* %gc_malloc_atomic(UINT %n) {
    %nn  = cast UINT %n to uint
    %ptr = malloc sbyte, uint %nn
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
