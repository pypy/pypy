
entrycode = '''
ccc %(returntype)s %%__entrypoint__%(entrypointname)s {
    call fastcc void %%pypy_rpyexc_clear()
    %%result = call %(cconv)s %(returntype)s%%%(entrypointname)s
    ret %(returntype)s %%result
}
'''

voidentrycode = '''
ccc %(returntype)s %%__entrypoint__%(entrypointname)s {
    call fastcc void %%pypy_rpyexc_clear()
    call %(cconv)s %(returntype)s%%%(entrypointname)s
    ret void
}
'''

raisedcode = '''
ccc bool %%__entrypoint__raised_LLVMException() {
    %%result = call fastcc bool %%pypy_rpyexc_occured()
    ret bool %%result
}
'''
