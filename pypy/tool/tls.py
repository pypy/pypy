"""Thread-local storage."""

try:
    from thread import _local as tlsobject
except ImportError:   # Python < 2.4

    # XXX needs a real object whose attributes are visible only in
    #     the thread that reads/writes them.

    class tlsobject(object):
        pass
