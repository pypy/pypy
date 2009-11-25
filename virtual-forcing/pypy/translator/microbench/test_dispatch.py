try:
    import dis
    import new
except ImportError:
    pass
else:
    import sys

    N_NOPS = 10**7
    N = int(50)

    codestr = ""
    ccode = compile(codestr, '<string>', 'exec')
    mycode = N_NOPS * chr(dis.opmap['NOP']) + ccode.co_code
    co = new.code(ccode.co_argcount,
        ccode.co_nlocals,
        ccode.co_stacksize, 
        ccode.co_flags,
        mycode,
        ccode.co_consts,
        ccode.co_names,
        ccode.co_varnames,
        ccode.co_filename,
        ccode.co_name,
        ccode.co_firstlineno,
        ccode.co_lnotab,
        ccode.co_freevars,
        ccode.co_cellvars)

    def test_dispatch_nop():
        x = 0
        n = N
        while x < n:
            exec co
            x += 1
            #sys.stdout.write('.')
            #sys.stdout.flush()
