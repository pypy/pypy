"""
Plain Python definition of some miscellaneous builtin functions.
"""


_stringtable = {}
def intern(s):
    # XXX CPython has also non-immortal interned strings
    if not type(s) is str: 
        raise TypeError("intern() argument 1 must be string.")
    return _stringtable.setdefault(s,s)

def find_module(fullname,  path):
    import sys
    meta_path = sys.meta_path
    for hook in meta_path:
        loader = hook.find_module(fullname,  path)
        if loader:
            return loader
    if path != None and type(path) == str:
       pass
       # XXX Check for frozen modules ?
    if path == None:
       # XXX Check frozen
       path = sys.path
    path_hooks = sys.path_hooks
    importer_cache = sys.path_importer_cache 
    importer = None
    for p in path:
        if importer_cache.get(p,None):
            importer = importer_cache.get(p)
        else:
            importer_cache[p] = None
            for hook in path_hooks:
                try:
                    importer = hook(p)
                except ImportError:
                    pass
                else:
                    break
            if importer:
                importer_cache[p] = importer
        if importer:
            loader = importer.find_module(fullname)
            if loader:
                return loader
     #no hooks match - do normal import

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
    loader = find_module(name, path)
    if loader:
        mod = loader.load_module(name)
        if mod:
            return mod

    f, filename, description = imp.find_module(subname, path)
    try:
        new_module = imp.load_module(name, f, filename, description)
    finally:
        sys.modules[name] = module
        if f is not None:
            f.close()

    return new_module
