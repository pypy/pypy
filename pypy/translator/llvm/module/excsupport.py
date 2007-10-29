
entrycode = '''
ccc %(returntype)s%%__entrypoint__%(entrypointname)s {
    store %%RPYTHON_EXCEPTION_VTABLE* null, %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    %%result = call %(cconv)s %(returntype)s%%%(entrypointname)s
    %%tmp    = load %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    %%exc    = seteq %%RPYTHON_EXCEPTION_VTABLE* %%tmp, null
    br bool %%exc, label %%no_exception, label %%exception

no_exception:
    ret %(returntype)s %%result

exception:
    ret %(noresult)s
}
'''

voidentrycode = '''
ccc %(returntype)s%%__entrypoint__%(entrypointname)s {
    store %%RPYTHON_EXCEPTION_VTABLE* null, %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    call %(cconv)s %(returntype)s%%%(entrypointname)s
    ret void
}
'''

raisedcode = '''
;XXX this should use the transformation data that has the same purpose
ccc int %%__entrypoint__raised_LLVMException() {
    %%tmp    = load %%RPYTHON_EXCEPTION_VTABLE** %%last_exception_type
    %%result = cast %%RPYTHON_EXCEPTION_VTABLE* %%tmp to int
    ret int %%result
}

'''
