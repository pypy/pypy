extdeclarations =  """;rpython stuff

;gc-type dependent mallocs
declare fastcc sbyte* %gc_malloc(uint)
declare fastcc sbyte* %gc_malloc_atomic(uint)

;exception handling globals
%last_exception_type  = global %RPYTHON_EXCEPTION_VTABLE* null
%last_exception_value = global %RPYTHON_EXCEPTION* null
"""

extfunctions = {}   #dependencies, llvm-code

import support

for module in (support,):
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
