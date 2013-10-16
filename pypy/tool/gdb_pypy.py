"""
Some convenience macros for gdb.  If you have pypy in your path, you can simply do:

(gdb) python import pypy.tool.gdb_pypy

Or, alternatively:

(gdb) python execfile('/path/to/gdb_pypy.py')
"""

from __future__ import with_statement

import re
import sys
import os.path

try:
    # when running inside gdb
    from gdb import Command
except ImportError:
    # whenn running outside gdb: mock class for testing
    class Command(object):
        def __init__(self, name, command_class):
            pass

MAX_DISPLAY_LENGTH = 100 # maximum number of characters displayed in rpy_string

def find_field_with_suffix(val, suffix):
    """
    Return ``val[field]``, where ``field`` is the only one whose name ends
    with ``suffix``.  If there is no such field, or more than one, raise KeyError.
    """
    names = []
    for field in val.type.fields():
        if field.name.endswith(suffix):
            names.append(field.name)
    #
    if len(names) == 1:
        return val[names[0]]
    elif len(names) == 0:
        raise KeyError, "cannot find field *%s" % suffix
    else:
        raise KeyError, "too many matching fields: %s" % ', '.join(names)

def lookup(val, suffix):
    """
    Lookup a field which ends with ``suffix`` following the rpython struct
    inheritance hierarchy (i.e., looking both at ``val`` and
    ``val['*_super']``, recursively.
    """
    try:
        return find_field_with_suffix(val, suffix)
    except KeyError:
        baseobj = find_field_with_suffix(val, '_super')
        return lookup(baseobj, suffix)


class RPyType(Command):
    """
    Prints the RPython type of the expression (remember to dereference it!)
    It assumes to find ``typeids.txt`` in the current directory.
    E.g.:

    (gdb) rpy_type *l_v123
    GcStruct pypy.foo.Bar { super, inst_xxx, inst_yyy }
    """

    prog2typeids = {}

    def __init__(self, gdb=None):
        # dependency injection, for tests
        if gdb is None:
            import gdb
        self.gdb = gdb
        Command.__init__(self, "rpy_type", self.gdb.COMMAND_NONE)

    def invoke(self, arg, from_tty):
        # some magic code to automatically reload the python file while developing
        from pypy.tool import gdb_pypy
        reload(gdb_pypy)
        gdb_pypy.RPyType.prog2typeids = self.prog2typeids # persist the cache
        self.__class__ = gdb_pypy.RPyType
        print self.do_invoke(arg, from_tty)

    def do_invoke(self, arg, from_tty):
        try:
            offset = int(arg)
        except ValueError:
            obj = self.gdb.parse_and_eval(arg)
            hdr = lookup(obj, '_gcheader')
            tid = hdr['h_tid']
            offset = tid & 0xFFFFFFFF # 64bit only
            offset = int(offset) # convert from gdb.Value to python int

        typeids = self.get_typeids()
        if offset in typeids:
            return typeids[offset]
        else:
            return 'Cannot find the type with offset %d' % offset

    def get_typeids(self):
        progspace = self.gdb.current_progspace()
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
        # XXX The same information is found in
        # XXX   pypy_g_rpython_memory_gctypelayout_GCData.gcd_inst_typeids_z
        # XXX Find out how to read it
        typeids_txt = os.path.join(root, 'typeids.txt')
        if not os.path.exists(typeids_txt):
            newroot = os.path.dirname(root)
            typeids_txt = os.path.join(newroot, 'typeids.txt')
        print 'loading', typeids_txt
        with open(typeids_txt) as f:
            typeids = TypeIdsMap(f.readlines(), self.gdb)
        return typeids


class TypeIdsMap(object):
    def __init__(self, lines, gdb):
        self.lines = lines
        self.gdb = gdb
        self.line2offset = {0: 0}
        self.offset2descr = {0: "(null typeid)"}

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __contains__(self, key):
        return self.get(key) is not None

    def _fetchline(self, linenum):
        if linenum in self.line2offset:
            return self.line2offset[linenum]
        line = self.lines[linenum]
        member, descr = map(str.strip, line.split(None, 1))
        if sys.maxint < 2**32:
            TIDT = "int*"
        else:
            TIDT = "char*"
        expr = ("((%s)(&pypy_g_typeinfo.%s)) - (%s)&pypy_g_typeinfo"
                   % (TIDT, member, TIDT))
        offset = int(self.gdb.parse_and_eval(expr))
        self.line2offset[linenum] = offset
        self.offset2descr[offset] = descr
        return offset

    def get(self, offset, default=None):
        # binary search through the lines, asking gdb to parse stuff lazily
        if offset in self.offset2descr:
            return self.offset2descr[offset]
        if not (0 < offset < sys.maxint):
            return None
        linerange = (0, len(self.lines))
        while linerange[0] < linerange[1]:
            linemiddle = (linerange[0] + linerange[1]) >> 1
            offsetmiddle = self._fetchline(linemiddle)
            if offsetmiddle == offset:
                return self.offset2descr[offset]
            elif offsetmiddle < offset:
                linerange = (linemiddle + 1, linerange[1])
            else:
                linerange = (linerange[0], linemiddle)
        return None


def is_ptr(type, gdb):
    if gdb is None:
        import gdb # so we can pass a fake one from the tests
    return type.code == gdb.TYPE_CODE_PTR


class RPyStringPrinter(object):
    """
    Pretty printer for rpython strings.

    Note that this pretty prints *pointers* to strings: this way you can do "p
    val" and see the nice string, and "p *val" to see the underyling struct
    fields
    """

    def __init__(self, val):
        self.val = val

    @classmethod
    def lookup(cls, val, gdb=None):
        t = val.type
        if is_ptr(t, gdb) and t.target().tag == 'pypy_rpy_string0':
            return cls(val)
        return None

    def to_string(self):
        chars = self.val['rs_chars']
        length = int(chars['length'])
        items = chars['items']
        res = []
        for i in range(min(length, MAX_DISPLAY_LENGTH)):
            try:
                res.append(chr(items[i]))
            except ValueError:
                # it's a gdb.Value so it has "121 'y'" as repr
                res.append(chr(int(str(items[0]).split(" ")[0])))
        if length > MAX_DISPLAY_LENGTH:
            res.append('...')
        string = ''.join(res)
        return 'r' + repr(string)


class RPyListPrinter(object):
    """
    Pretty printer for rpython lists

    Note that this pretty prints *pointers* to lists: this way you can do "p
    val" and see the nice repr, and "p *val" to see the underyling struct
    fields
    """

    def __init__(self, val):
        self.val = val

    @classmethod
    def lookup(cls, val, gdb=None):
        t = val.type
        if (is_ptr(t, gdb) and t.target().tag is not None and
            re.match(r'pypy_list\d*', t.target().tag)):
            return cls(val)
        return None

    def to_string(self):
        length = int(self.val['l_length'])
        array = self.val['l_items']
        allocated = int(array['length'])
        items = array['items']
        itemlist = []
        for i in range(length):
            item = items[i]
            itemlist.append(str(item))
        str_items = ', '.join(itemlist)
        return 'r[%s] (len=%d, alloc=%d)' % (str_items, length, allocated)


try:
    import gdb
    RPyType() # side effects
    gdb.pretty_printers += [
        RPyStringPrinter.lookup,
        RPyListPrinter.lookup
        ]
except ImportError:
    pass
