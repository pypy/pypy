
"""Thread-local storage."""

try:
    from thread import _local as tlsobject
except ImportError:
    class tlsobject(object):
        pass
