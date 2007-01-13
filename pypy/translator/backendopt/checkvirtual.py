"""
Visit all known INSTANCEs to see which methods can be marked as
non-virtual: a method is marked as non-virtual when it's never
overridden in the subclasses: this means that backends can translate
oosends relative to that method into non-virtual call (or maybe
switching back to a direct_call if the backend doesn't support
non-virtual calls, such as JVM).
"""

from pypy.rpython.ootypesystem import ootype

def check_virtual_methods(INSTANCE=ootype.ROOT, super_methods = {}):
    my_methods = super_methods.copy()
    for name, method in INSTANCE._methods.iteritems():
        method._virtual = False
        my_methods[name] = method
        if name in super_methods:
            super_methods[name]._virtual = True

    for SUB_INSTANCE in INSTANCE._subclasses:
        check_virtual_methods(SUB_INSTANCE, my_methods)
