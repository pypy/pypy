import sys

if 'thread' in sys.builtin_module_names:
    from thread import _local as local
elif 'transaction' in sys.builtin_module_names:
    from transaction import local
else:
    class local(object):
        """A pseudo-thread-local class.
        As this interpreter does not have threads, it is a regular class.
        """
