"""
Some convenience macros for gdb.  If you have pypy in your path, you can simply do:

(gdb) python import pypy.tool.gdb_pypy

Or, alternatively:

(gdb) python execfile('/path/to/gdb_pypy.py')
"""

import sys
import os.path
import gdb

class RPyType (gdb.Command):
    """
    Prints the RPython type of the expression (remember to dereference it!)
    It assumes to find ``typeids.txt`` in the current directory.
    E.g.:

    (gdb) rpy_type *l_v123
    GcStruct pypy.foo.Bar { super, inst_xxx, inst_yyy }
    """

    prog2typeids = {}
 
    def __init__(self):
        gdb.Command.__init__(self, "rpy_type", gdb.COMMAND_NONE)

    # some magic code to automatically reload the python file while developing
    def invoke(self, arg, from_tty):
        from pypy.tool import gdb_pypy
        reload(gdb_pypy)
        gdb_pypy.RPyType.prog2typeids = self.prog2typeids # persist the cache
        self.__class__ = gdb_pypy.RPyType
        self.do_invoke(arg, from_tty)

    def do_invoke(self, arg, from_tty):
        obj = gdb.parse_and_eval(arg)
        hdr = self.get_gc_header(obj)
        tid = hdr['h_tid']
        offset = tid & 0xFFFFFFFF # 64bit only
        offset = int(offset) # convert from gdb.Value to python int
        typeids = self.get_typeids()
        if offset in typeids:
            print typeids[offset]
        else:
            print 'Cannot find the type with offset %d' % offset

    def get_typeids(self):
        progspace = gdb.current_progspace()
        try:
            return self.prog2typeids[progspace]
        except KeyError:
            typeids = self.load_typeids(progspace)
            self.prog2typeids[progspace] = typeids
            return typeids

    def load_typeids(self, progspace):
        """
        Returns a mapping offset --> description
        """
        exename = progspace.filename
        root = os.path.dirname(exename)
        typeids_txt = os.path.join(root, 'typeids.txt')
        print 'loading', typeids_txt
        typeids = {}
        for line in open('typeids.txt'):
            member, descr = map(str.strip, line.split(None, 1))
            expr = "((char*)(&pypy_g_typeinfo.%s)) - (char*)&pypy_g_typeinfo" % member
            offset = int(gdb.parse_and_eval(expr))
            typeids[offset] = descr
        return typeids

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
