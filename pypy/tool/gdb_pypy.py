"""
Some convenience macros for gdb.  Load them by putting this file somewhere in
the path and then, from gdb:

(gdb) python import pypy_gdb

Or, alternatively:

(gdb) python execfile('/path/to/pypy_gdb.py')
"""

import sys
import gdb

def load_typeids():
    """
    Returns a mapping offset --> description
    """
    typeids = {}
    for line in open('typeids.txt'):
        member, descr = map(str.strip, line.split(None, 1))
        expr = "((char*)(&pypy_g_typeinfo.%s)) - (char*)&pypy_g_typeinfo" % member
        offset = int(gdb.parse_and_eval(expr))
        typeids[offset] = descr
    return typeids

class RPyType (gdb.Command):
    """
    Prints the RPython type of the expression (remember to dereference it!)
    It assumes to find ``typeids.txt`` in the current directory.
    E.g.:

    (gdb) rpy_type *l_v123
    GcStruct pypy.foo.Bar { super, inst_xxx, inst_yyy }
    """
 
    def __init__(self):
        gdb.Command.__init__(self, "rpy_type", gdb.COMMAND_NONE)

    ## # some magic code to automatically reload the python file while developing
    ## def invoke(self, arg, from_tty):
    ##     sys.path.insert(0, '')
    ##     import gdb_pypy
    ##     reload(gdb_pypy)
    ##     self.__class__ = gdb_pypy.RPyType
    ##     self.do_invoke(arg, from_tty)

    def invoke(self, arg, from_tty):
        obj = gdb.parse_and_eval(arg)
        hdr = self.get_gc_header(obj)
        tid = hdr['h_tid']
        offset = tid & 0xFFFFFFFF # 64bit only
        offset = int(offset) # convert from gdb.Value to python int
        typeids = load_typeids()
        if offset in typeids:
            print typeids[offset]
        else:
            print 'Cannot find the type with offset %d' % offset

    def get_first_field_if(self, obj, suffix):
        ctype = obj.type
        field = ctype.fields()[0]
        if field.name.endswith(suffix):
            return obj[field.name]
        return None

    def get_super(self, obj):
        return self.get_first_field_if(obj, '_super')

    def get_gc_header(self, obj):
        while True:
            sup = self.get_super(obj)
            if sup is None:
                break
            obj = sup
        return self.get_first_field_if(obj, '_gcheader')

RPyType() # side effects
