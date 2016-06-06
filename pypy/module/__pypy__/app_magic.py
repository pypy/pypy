

def _unroll_safe(func):
    """ Decorator to mark a function as unroll-safe, meaning the JIT will not
    trace any of the loops in the function. Instead, the loops will be unrolled
    fully into the caller.

    This function is experimental.
    """
    # bit of a hack: replace JUMP_ABSOLUTE bytecode with JUMP_ABSOLUTE_UNROLL,
    # which will not trigger jitting
    from opcode import opname, HAVE_ARGUMENT, EXTENDED_ARG, opmap
    from types import CodeType, FunctionType
    code = list(func.func_code.co_code)
    n = len(code)
    i = 0
    replaced = False
    while i < n:
        orig_i = i
        c = code[i]
        op = ord(c)
        i = i+1
        if op >= HAVE_ARGUMENT:
            i = i+2
            if op == opmap['JUMP_ABSOLUTE']:
                replaced = True
                code[orig_i] = chr(opmap['JUMP_ABSOLUTE_UNROLL'])
    if not replaced:
        raise TypeError("function %s does not contain a loop" % func)
    new_codestring = "".join(code)
    code = func.func_code
    new_code = CodeType(code.co_argcount, code.co_nlocals, code.co_stacksize,
            code.co_flags, new_codestring, code.co_consts, code.co_names,
            code.co_varnames, code.co_filename, code.co_name, code.co_firstlineno,
            code.co_lnotab, code.co_freevars, code.co_cellvars)
    f = FunctionType(new_code, func.func_globals, func.func_name,
                     func.func_defaults, func.func_closure)
    if func.func_dict:
        f.func_dict = {}
        f.func_dict.update(func.func_dict)
    f.func_doc = func.func_doc
    return f
