extdeclarations =  '''
%last_exception_type  = internal global %RPYTHON_EXCEPTION_VTABLE* null
%last_exception_value = internal global %RPYTHON_EXCEPTION* null

;8208=8192+16 in the next line because the last one (16 bytes maxsize) might start at 8190 for instance.
%exception_ringbuffer = internal global [8208 x sbyte] zeroinitializer
%exception_ringbuffer_index = internal global uint 0
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
