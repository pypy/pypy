"""
Tool functions regarding local filesystem paths
"""
from py import path 

def get_temproot():
    """ return the system's temporary directory (where tempfiles are usually created in)"""
    p = mkdtemp()
    try:
        return p.dirpath()
    finally:
        p.remove()
    
def mkdtemp():
    """ return a Path object pointing to a fresh new temporary directory
    (which we created ourself).  
    """
    import tempfile
    tries = 10
    for i in range(tries):
        dname = tempfile.mktemp()
        dpath = path.local(tempfile.mktemp()) 
        try:
            dpath.mkdir()
        except path.FileExists:
            continue
        return dpath
    raise NotFound, "could not create tempdir, %d tries" % tries

def make_numbered_dir(rootdir=None, base = 'session-', keep=3):
    """ return unique directory with a number greater than the current
        maximum one.  The number is assumed to start directly after base. 
        if keep is true directories with a number less than (maxnum-keep)
        will be removed. 
    """
    if rootdir is None:
        rootdir = get_temproot()

    def parse_num(path):
        """ parse the number out of a path (if it matches the base) """
        bn = path.basename 
        if bn.startswith(base):
            try:
                return int(bn[len(base):])
            except TypeError:
                pass

    # compute the maximum number currently in use with the base
    maxnum = -1
    for path in rootdir.listdir():
        num = parse_num(path)
        if num is not None:
            maxnum = max(maxnum, num)

    # make the new directory 
    udir = rootdir.mkdir(base + str(maxnum+1))

    # prune old directories
    if keep: 
        for path in rootdir.listdir():
            num = parse_num(path)
            if num is not None and num <= (maxnum - keep):
                path.remove(rec=1)
    return udir

def parentdirmatch(dirname, startmodule=None):
    if startmodule is None:
        fn = path.local()
    else:
        mod = path.py(startmodule) 
        fn = mod.getfile()
    current = fn.dirpath()
    while current != fn:
        fn = current
        if current.basename == dirname:
            return current
        current = current.dirpath()
