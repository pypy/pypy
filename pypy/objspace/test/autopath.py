"""
self cloning, automatic path configuration 

copy this into any subdirectory of pypy from which scripts need 
to be run, typically all of the test subdirs. 
The idea is that any such script simply issues

    import autopath

and this will make sure that the parent directory containing "pypy"
is in sys.path. 

If you modify the master "autopath.py" version (in pypy/tool/autopath.py) 
you can directly run it which will copy itself on all autopath.py files
it finds under the pypy root directory. 

This module always provides these attributes:

    pypydir    pypy root directory path 
    this_dir   directory where this autopath.py resides 

"""


def __dirinfo(part):
    """ return (partdir, this_dir) and insert parent of partdir
    into sys.path.  If the parent directories don't have the part
    an EnvironmentError is raised."""

    import sys, os
    try:
        head = this_dir = os.path.realpath(os.path.dirname(__file__))
    except NameError:
        head = this_dir = os.path.realpath(os.path.dirname(sys.argv[0]))

    while head:
        partdir = head
        head, tail = os.path.split(head)
        if tail == part:
            break
    else:
        raise EnvironmentError, "'%s' missing in '%r'" % (partdir, this_dir)
    
    checkpaths = sys.path[:]
    pypy_root = os.path.join(head, '')
    
    while checkpaths:
        orig = checkpaths.pop()
        if os.path.join(os.path.realpath(orig), '').startswith(pypy_root):
            sys.path.remove(orig)
    sys.path.insert(0, head)

    munged = {}
    for name, mod in sys.modules.items():
        fn = getattr(mod, '__file__', None)
        if '.' in name or not isinstance(fn, str):
            continue
        newname = os.path.splitext(os.path.basename(fn))[0]
        path = os.path.join(os.path.dirname(os.path.realpath(fn)), '')
        if path.startswith(pypy_root) and newname != part:
            modpaths = os.path.normpath(path[len(pypy_root):]).split(os.sep)
            if newname != '__init__':
                modpaths.append(newname)
            modpath = '.'.join(modpaths)
            if modpath not in sys.modules:
                munged[modpath] = mod

    for name, mod in munged.iteritems():
        if name not in sys.modules:
            sys.modules[name] = mod
        if '.' in name:
            prename = name[:name.rfind('.')]
            postname = name[len(prename)+1:]
            if prename not in sys.modules:
                __import__(prename)
                if not hasattr(sys.modules[prename], postname):
                    setattr(sys.modules[prename], postname, mod)

    return partdir, this_dir

def __clone():
    """ clone master version of autopath.py into all subdirs """
    from os.path import join, walk
    if not this_dir.endswith(join('pypy','tool')):
        raise EnvironmentError("can only clone master version "
                               "'%s'" % join(pypydir, 'tool',_myname))


    def sync_walker(arg, dirname, fnames):
        if _myname in fnames:
            fn = join(dirname, _myname)
            f = open(fn, 'rwb+')
            try:
                if f.read() == arg:
                    print "checkok", fn
                else:
                    print "syncing", fn
                    f = open(fn, 'w')
                    f.write(arg)
            finally:
                f.close()
    s = open(join(pypydir, 'tool', _myname), 'rb').read()
    walk(pypydir, sync_walker, s)

_myname = 'autopath.py'

# set guaranteed attributes

pypydir, this_dir = __dirinfo('pypy')

if __name__ == '__main__':
    __clone()
