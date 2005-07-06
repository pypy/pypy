extdeclarations = """; External declarations

declare int %dup(int)

; End of external declarations
"""

extfunctions = """; External functions (will be inlined by LLVM)

int %ll_os_dup__Signed(int %i) {
block0:
    %i.0 = call int %dup(int %i)
    ret int %i.0
}

; End of external functions
"""
