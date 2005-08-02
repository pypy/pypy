extdeclarations =  """;rpython stuff
%structtype.rpy_string = type {int, {int, [0 x sbyte]}}

;gc-type dependent mallocs
declare fastcc sbyte* %gc_malloc(uint)
declare fastcc sbyte* %gc_malloc_atomic(uint)

;exception handling globals
%last_exception_type  = global %structtype.object_vtable* null
%last_exception_value = global %structtype.object* null
"""

gc_boehm = """declare ccc sbyte* %GC_malloc(uint)
declare ccc sbyte* %GC_malloc_atomic(uint)

fastcc sbyte* %gc_malloc(uint %n) {
    %ptr = call ccc sbyte* %GC_malloc(uint %n)
    ret sbyte* %ptr
}

fastcc sbyte* %gc_malloc_atomic(uint %n) {
    %ptr = call ccc sbyte* %GC_malloc_atomic(uint %n)
    ret sbyte* %ptr
}
"""

gc_disabled = """fastcc sbyte* %gc_malloc(uint %n) {
    %ptr = malloc sbyte, uint %n
    ret sbyte* %ptr
}

fastcc sbyte* %gc_malloc_atomic(uint %n) {
    %ptr = malloc sbyte, uint %n
    ret sbyte* %ptr
}
"""

extfunctions = {}   #dependencies, llvm-code

import support, ll_os, ll_os_path, ll_time, ll_math

for module in (support, ll_os, ll_os_path, ll_time, ll_math):
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
