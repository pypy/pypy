"""Thread-local storage."""

try:
    from thread import _local as tlsobject
except ImportError:   # Python < 2.4

    # XXX needs a real object whose attributes are visible only in
    #     the thread that reads/writes them.

    import autopath, os
    filename = os.path.join(os.path.dirname(autopath.pypydir),
                            'lib-python', '2.4.1', '_threading_local.py')
    glob = {'__name__': '_threading_local'}
    execfile(filename, glob)
    tlsobject = glob['local']
    del glob, filename
