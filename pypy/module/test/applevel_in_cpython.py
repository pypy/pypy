"""
Hack to (partially) import the app-level parts of PyPy modules
directly in CPython, when the goal is to test these app-level parts and
not necessarily PyPy's interpretation of them.
"""

import autopath, new, sys


def applevel_in_cpython(modulename):
    try:
        real_mod = __import__(modulename)
    except ImportError:
        real_mod = None

    class DunnoType:
        def __repr__(self):
            return "<this would come from interp-level if we had one>"
    Dunno = DunnoType()

    def ouack_eval(s):
        return {
            'space.w_None': None,
            'space.w_False': False,
            'space.w_True': True,
            'space.w_type': type,
            'space.w_object': object,
            'space.wrap(unicode)': unicode,
            'space.wrap(file)': file,
            }.get(s, Dunno)

    def ouack_execfile(s):
        pass

    class OuackModule:
        def __getattr__(self, name):
            return getattr(real_mod, name, Dunno)
    ouack_module = OuackModule()
    ouack_module._issubtype = issubclass


    from os.path import join
    filename = join(autopath.pypydir, 'module', '%smodule.py' % modulename)
    mod = new.module('applevel_in_cpython:%s' % modulename)
    mod.__dict__.update({
        '__file__': filename,
        '__interplevel__eval': ouack_eval,
        '__interplevel__execfile': ouack_execfile,
        })
    sys.modules['__interplevel__'] = ouack_module
    try:
        execfile(filename, mod.__dict__)
    finally:
        del sys.modules['__interplevel__']
    return mod
