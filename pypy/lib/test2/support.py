import sys, os, new

this_dir = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))
lib_dir  = os.path.dirname(this_dir)
pypy_dir = os.path.dirname(lib_dir)
dist_dir = os.path.dirname(pypy_dir)

if dist_dir not in sys.path:
    sys.path.insert(0, dist_dir)

def cleanup_path():
    # the 'pypy/lib' directory should always be last in CPython's sys.path,
    # after the standard library!
    sys.path[:] = [p for p in sys.path
                     if os.path.normpath(os.path.abspath(p)) != lib_dir]
    sys.path.append(lib_dir)

cleanup_path()


def libmodule(modname):
    """Get a module from the pypy/lib directory, without going through the
    import machinery.
    """
    # forces the real CPython module to be imported first, to avoid strange
    # interactions later
    cleanup_path()
    cpython_mod = __import__(modname)
    if hasattr(cpython_mod, '__file__'):
        assert os.path.dirname(cpython_mod.__file__) != lib_dir
    filename = os.path.join(lib_dir, modname + '.py')
    mod = new.module(modname)
    mod.__file__ = filename
    execfile(filename, mod.__dict__)
    return mod
