"""
Plain Python definition of some miscellaneous builtin functions.
"""


_stringtable = {}
def intern(s):
    # XXX CPython has also non-immortal interned strings
    if not isinstance(s, str):
        raise TypeError("intern() argument 1 must be string.")
    return _stringtable.setdefault(s,s)


def reload(module):
    import imp, sys, errno

    if type(module) not in (type(imp), type(errno)):
        raise TypeError("reload() argument must be module")

    name = module.__name__
    if module is not sys.modules[name]:
        raise ImportError("reload(): module %.200s not in sys.modules" % name)

    namepath = name.split('.')
    subname = namepath[-1]
    parent_name = '.'.join(namepath[:-1])
    parent = None
    path = None
    if parent_name:
        try:
            parent = sys.modules[parent_name]
        except KeyError:
            raise ImportError("reload(): parent %.200s not in sys.modules" %
                              parent_name)
        path = parent.__path__

    f, filename, description = imp.find_module(subname, path)
    try:
        new_module = imp.load_module(name, f, filename, description)
    finally:
        sys.modules[name] = module
        if f is not None:
            f.close()

    return new_module
