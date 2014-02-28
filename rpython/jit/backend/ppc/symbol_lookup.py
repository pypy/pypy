
def lookup(sym):
    global lookup
    import py

    _ppcgen = py.magic.autopath().dirpath().join('_ppcgen.c')._getpymodule()

    try:
        from _ppcgen import NSLookupAndBindSymbol

        def lookup(sym):
            return NSLookupAndBindSymbol('_' + sym)
    except ImportError:
        from _ppcgen import dlsym as lookup
    return lookup(sym)
