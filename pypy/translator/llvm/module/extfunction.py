extdeclarations =  '''
%last_exception_type  = internal global %RPYTHON_EXCEPTION_VTABLE* null
%last_exception_value = internal global %RPYTHON_EXCEPTION* null

%exception_ringbuffer = internal global [8192 x sbyte] zeroinitializer
%exception_ringbuffer_index = internal global int 0
'''

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
