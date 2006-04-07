#! /usr/bin/env python

import os, py
import ctypes
from pypy.translator.tool.cbuild import build_executable
from pypy.tool.udir import udir


def uniquefilepath(LAST=[0]):
    i = LAST[0]
    LAST[0] += 1
    return udir.join('ctypesplatcheck_%d.c' % i)

alignment_types = [
    ctypes.c_short,
    ctypes.c_int,
    ctypes.c_long,
    ctypes.c_float,
    ctypes.c_double,
    ctypes.c_char_p,
    ctypes.c_void_p,
    ctypes.c_longlong,
    ctypes.c_wchar,
    ctypes.c_wchar_p,
    ]

integer_class = [ctypes.c_byte,     ctypes.c_ubyte,
                 ctypes.c_short,    ctypes.c_ushort,
                 ctypes.c_int,      ctypes.c_uint,
                 ctypes.c_long,     ctypes.c_ulong,
                 ctypes.c_longlong, ctypes.c_ulonglong,
                 ]
float_class = [ctypes.c_float, ctypes.c_double]

class Field(object):
    def __init__(self, name, ctype):
        self.name = name
        self.ctype = ctype
    def __repr__(self):
        return '<field %s: %s>' % (self.name, self.ctype)

def layout_addfield(layout, offset, ctype, prefix):
    size = ctypes.sizeof(ctype)
    name = prefix
    i = 0
    while name in layout:
        i += 1
        name = '%s_%d' % (prefix, i)
    field = Field(name, ctype)
    for i in range(offset, offset+size):
        assert layout[i] is None, "%s overlaps %r" % (fieldname, layout[i])
        layout[i] = field
    return field

def size_and_sign(ctype):
    return (ctypes.sizeof(ctype),
            ctype in integer_class and ctype(-1).value > 0)

def fixup_ctype(fieldtype, fieldname, expected_size_and_sign):
    for typeclass in [integer_class, float_class]:
        if fieldtype in typeclass:
            for ctype in typeclass:
                if size_and_sign(ctype) == expected_size_and_sign:
                    return ctype
    raise TypeError("conflicting field type %r for %r" % (fieldtype,
                                                          fieldname))


C_HEADER = """
#include <stdio.h>
#include <stddef.h>   /* for offsetof() */

void dump(char* key, int value) {
    printf("%s: %d\\n", key, value);
}
"""

def run_example_code(filepath):
    executable = build_executable([filepath])
    output = py.process.cmdexec(executable)
    info = {}
    for line in output.splitlines():
        key, value = line.strip().split(': ')
        info[key] = int(value)
    return info

def getstruct(name, c_header_source, interesting_fields):
    filepath = uniquefilepath()
    f = filepath.open('w')
    print >> f, C_HEADER
    print >> f
    print >> f, c_header_source
    print >> f
    print >> f, 'typedef %s ctypesplatcheck_t;' % (name,)
    print >> f, 'typedef struct {'
    print >> f, '    char c;'
    print >> f, '    ctypesplatcheck_t s;'
    print >> f, '} ctypesplatcheck2_t;'
    print >> f
    print >> f, 'int main(void) {'
    print >> f, '    ctypesplatcheck_t s;'
    print >> f, '    dump("align", offsetof(ctypesplatcheck2_t, s));'
    print >> f, '    dump("size",  sizeof(ctypesplatcheck_t));'
    for fieldname, fieldtype in interesting_fields:
        print >> f, '    dump("fldofs %s", offsetof(ctypesplatcheck_t, %s));'%(
            fieldname, fieldname)
        print >> f, '    dump("fldsize %s",   sizeof(s.%s));' % (
            fieldname, fieldname)
        if fieldtype in integer_class:
            print >> f, '    s.%s = 0; s.%s = ~s.%s;' % (fieldname,
                                                         fieldname,
                                                         fieldname)
            print >> f, '    dump("fldunsigned %s", s.%s > 0);' % (fieldname,
                                                                   fieldname)
    print >> f, '    return 0;'
    print >> f, '}'
    f.close()

    info = run_example_code(filepath)

    alignment = 1
    layout = [None] * info['size']
    for fieldname, fieldtype in interesting_fields:
        offset = info['fldofs '  + fieldname]
        size   = info['fldsize ' + fieldname]
        sign   = info.get('fldunsigned ' + fieldname, False)
        if (size, sign) != size_and_sign(fieldtype):
            fieldtype = fixup_ctype(fieldtype, fieldname, (size, sign))
        layout_addfield(layout, offset, fieldtype, fieldname)
        alignment = max(alignment, ctypes.alignment(fieldtype))

    # try to enforce the same alignment as the one of the original structure
    if alignment < info['align']:
        choices = [ctype for ctype in alignment_types
                         if ctypes.alignment(ctype) == info['align']]
        assert choices, "unsupported alignment %d" % (info['align'],)
        choices = [(ctypes.sizeof(ctype), i, ctype)
                   for i, ctype in enumerate(choices)]
        csize, _, ctype = min(choices)
        for i in range(0, info['size'] - csize + 1, info['align']):
            if layout[i:i+csize] == [None] * csize:
                layout_addfield(layout, i, ctype, '_alignment')
                break
        else:
            raise AssertionError("unenforceable alignment %d" % (
                info['align'],))

    n = 0
    for i, cell in enumerate(layout):
        if cell is not None:
            continue
        layout_addfield(layout, i, ctypes.c_char, '_pad%d' % (n,))
        n += 1

    # build the ctypes Structure
    seen = {}
    fields = []
    for cell in layout:
        if cell in seen:
            continue
        fields.append((cell.name, cell.ctype))
        seen[cell] = True

    class S(ctypes.Structure):
        _fields_ = fields
    if name.startswith('struct '):
        name = name[7:]
    S.__name__ = name
    return S


def getsimpletype(name, c_header_source, ctype_hint):
    filepath = uniquefilepath()
    f = filepath.open('w')
    print >> f, C_HEADER
    print >> f
    print >> f, c_header_source
    print >> f
    print >> f, 'typedef %s ctypesplatcheck_t;' % (name,)
    print >> f
    print >> f, 'int main(void) {'
    print >> f, '    ctypesplatcheck_t x;'
    print >> f, '    dump("size",  sizeof(ctypesplatcheck_t));'
    if ctype_hint in integer_class:
        print >> f, '    x = 0; x = ~x;'
        print >> f, '    dump("unsigned", x > 0);'
    print >> f, '    return 0;'
    print >> f, '}'
    f.close()

    info = run_example_code(filepath)

    size = info['size']
    sign = info.get('unsigned', False)
    if (size, sign) != size_and_sign(ctype_hint):
        ctype_hint = fixup_ctype(ctype_hint, name, (size, sign))
    return ctype_hint


def getconstantinteger(name, c_header_source):
    filepath = uniquefilepath()
    f = filepath.open('w')
    print >> f, C_HEADER
    print >> f
    print >> f, c_header_source
    print >> f
    print >> f, 'int main(void) {'
    print >> f, '    if ((%s) < 0) {' % (name,)
    print >> f, '        long long x = (long long)(%s);' % (name,)
    print >> f, '        printf("value: %lld\\n", x);'
    print >> f, '    } else {'
    print >> f, '        unsigned long long x = (unsigned long long)(%s);' % (
                            name,)
    print >> f, '        printf("value: %llu\\n", x);'
    print >> f, '    }'
    print >> f, '    return 0;'
    print >> f, '}'
    f.close()

    info = run_example_code(filepath)

    return info['value']


if __name__ == '__main__':
    doc = """Example:
    
       ctypes_platform.py  -h sys/types.h  -h netinet/in.h
                           'struct sockaddr_in'
                           sin_port  c_int
    """
    import sys, getopt
    opts, args = getopt.gnu_getopt(sys.argv[1:], 'h:')
    if not args:
        print >> sys.stderr, doc
        sys.exit(2)
    assert len(args) % 2 == 1
    headers = []
    for opt, value in opts:
        if opt == '-h':
            headers.append('#include <%s>' % (value,))
    name = args[0]
    fields = []
    for i in range(1, len(args), 2):
        ctype = getattr(ctypes, args[i+1])
        fields.append((args[i], ctype))

    S = getstruct(name, '\n'.join(headers), fields)

    for key, value in S._fields_:
        print key, value
