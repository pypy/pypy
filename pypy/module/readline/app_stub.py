# NOT_RPYTHON

def stub(*args, **kwds):
    import warnings
    warnings.warn("the 'readline' module is only a stub so far")

def stub_str(*args, **kwds):
    stub()
    return ''

def stub_int(*args, **kwds):
    stub()
    return 0
