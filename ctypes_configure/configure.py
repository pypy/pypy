#! /usr/bin/env python

import os, py, sys
import ctypes
from ctypes_configure.cbuild import build_executable, configdir, try_compile
from ctypes_configure.cbuild import ExternalCompilationInfo
import distutils

# ____________________________________________________________
#
# Helpers for simple cases

def eci_from_header(c_header_source):
    return ExternalCompilationInfo(
        pre_include_lines=c_header_source.split("\n")
    )


def getstruct(name, c_header_source, interesting_fields):
    class CConfig:
        _compilation_info_ = eci_from_header(c_header_source)
        STRUCT = Struct(name, interesting_fields)
    return configure(CConfig)['STRUCT']

def getsimpletype(name, c_header_source, ctype_hint=ctypes.c_int):
    class CConfig:
        _compilation_info_ = eci_from_header(c_header_source)
        TYPE = SimpleType(name, ctype_hint)
    return configure(CConfig)['TYPE']

def getconstantinteger(name, c_header_source):
    class CConfig:
        _compilation_info_ = eci_from_header(c_header_source)
        CONST = ConstantInteger(name)
    return configure(CConfig)['CONST']

def getdefined(macro, c_header_source):
    class CConfig:
        _compilation_info_ = eci_from_header(c_header_source)
        DEFINED = Defined(macro)
    return configure(CConfig)['DEFINED']

def has(name, c_header_source):
    class CConfig:
        _compilation_info_ = eci_from_header(c_header_source)
        HAS = Has(name)
    return configure(CConfig)['HAS']

def check_eci(eci):
    """Check if a given ExternalCompilationInfo compiles and links."""
    class CConfig:
        _compilation_info_ = eci
        WORKS = Works()
    return configure(CConfig)['WORKS']

def sizeof(name, eci, **kwds):
    class CConfig:
        _compilation_info_ = eci
        SIZE = SizeOf(name)
    for k, v in kwds.items():
        setattr(CConfig, k, v)
    return configure(CConfig)['SIZE']

def memory_alignment():
    """Return the alignment (in bytes) of memory allocations.
    This is enough to make sure a structure with pointers and 'double'
    fields is properly aligned."""
    global _memory_alignment
    if _memory_alignment is None:
        S = getstruct('struct memory_alignment_test', """
           struct memory_alignment_test {
               double d;
               void* p;
           };
        """, [])
        result = ctypes.alignment(S)
        assert result & (result-1) == 0, "not a power of two??"
        _memory_alignment = result
    return _memory_alignment
_memory_alignment = None

# ____________________________________________________________
#
# General interface

class ConfigResult:
    def __init__(self, CConfig, info, entries):
        self.CConfig = CConfig
        self.result = {}
        self.info = info
        self.entries = entries
        
    def get_entry_result(self, entry):
        try:
            return self.result[entry]
        except KeyError:
            pass
        name = self.entries[entry]
        info = self.info[name]
        self.result[entry] = entry.build_result(info, self)

    def get_result(self):
        return dict([(name, self.result[entry])
                     for entry, name in self.entries.iteritems()])


class _CWriter(object):
    """ A simple class which aggregates config parts
    """
    def __init__(self, CConfig):
        self.path = uniquefilepath()
        self.f = self.path.open("w")
        self.config = CConfig

    def write_header(self):
        f = self.f
        CConfig = self.config
        CConfig._compilation_info_.write_c_header(f)
        print >> f, C_HEADER
        print >> f

    def write_entry(self, key, entry):
        f = self.f
        print >> f, 'void dump_section_%s(void) {' % (key,)
        for line in entry.prepare_code():
            if line and line[0] != '#':
                line = '\t' + line
            print >> f, line
        print >> f, '}'
        print >> f

    def write_entry_main(self, key):
        print >> self.f, '\tprintf("-+- %s\\n");' % (key,)
        print >> self.f, '\tdump_section_%s();' % (key,)
        print >> self.f, '\tprintf("---\\n");'

    def start_main(self):
        print >> self.f, 'int main(int argc, char *argv[]) {'

    def close(self):
        f = self.f
        print >> f, '\treturn 0;'
        print >> f, '}'
        f.close()

    def ask_gcc(self, question):
        self.start_main()
        self.f.write(question + "\n")
        self.close()
        eci = self.config._compilation_info_
        return try_compile([self.path], eci)

        
def configure(CConfig):
    """Examine the local system by running the C compiler.
    The CConfig class contains CConfigEntry attribues that describe
    what should be inspected; configure() returns a dict mapping
    names to the results.
    """
    for attr in ['_includes_', '_libraries_', '_sources_', '_library_dirs_',
                 '_include_dirs_', '_header_']:
        assert not hasattr(CConfig, attr), "Found legacy attribut %s on CConfig" % (attr,)
    entries = []
    for key in dir(CConfig):
        value = getattr(CConfig, key)
        if isinstance(value, CConfigEntry):
            entries.append((key, value))            

    if entries:   # can be empty if there are only CConfigSingleEntries
        writer = _CWriter(CConfig)
        writer.write_header()
        for key, entry in entries:
            writer.write_entry(key, entry)

        f = writer.f
        writer.start_main()
        for key, entry in entries:
            writer.write_entry_main(key)
        writer.close()

        eci = CConfig._compilation_info_
        infolist = list(run_example_code(writer.path, eci))
        assert len(infolist) == len(entries)

        resultinfo = {}
        resultentries = {}
        for info, (key, entry) in zip(infolist, entries):
            resultinfo[key] = info
            resultentries[entry] = key

        result = ConfigResult(CConfig, resultinfo, resultentries)
        for name, entry in entries:
            result.get_entry_result(entry)
        res = result.get_result()
    else:
        res = {}

    for key in dir(CConfig):
        value = getattr(CConfig, key)
        if isinstance(value, CConfigSingleEntry):
            writer = _CWriter(CConfig)
            writer.write_header()
            res[key] = value.question(writer.ask_gcc)

    return res

# ____________________________________________________________


class CConfigEntry(object):
    "Abstract base class."


class Struct(CConfigEntry):
    """An entry in a CConfig class that stands for an externally
    defined structure.
    """
    def __init__(self, name, interesting_fields, ifdef=None):
        self.name = name
        self.interesting_fields = interesting_fields
        self.ifdef = ifdef

    def prepare_code(self):
        if self.ifdef is not None:
            yield '#ifdef %s' % (self.ifdef,)
        yield 'typedef %s ctypesplatcheck_t;' % (self.name,)
        yield 'typedef struct {'
        yield '    char c;'
        yield '    ctypesplatcheck_t s;'
        yield '} ctypesplatcheck2_t;'
        yield ''
        yield 'ctypesplatcheck_t s;'
        if self.ifdef is not None:
            yield 'dump("defined", 1);'
        yield 'dump("align", offsetof(ctypesplatcheck2_t, s));'
        yield 'dump("size",  sizeof(ctypesplatcheck_t));'
        for fieldname, fieldtype in self.interesting_fields:
            yield 'dump("fldofs %s", offsetof(ctypesplatcheck_t, %s));'%(
                fieldname, fieldname)
            yield 'dump("fldsize %s",   sizeof(s.%s));' % (
                fieldname, fieldname)
            if fieldtype in integer_class:
                yield 's.%s = 0; s.%s = ~s.%s;' % (fieldname,
                                                   fieldname,
                                                   fieldname)
                yield 'dump("fldunsigned %s", s.%s > 0);' % (fieldname,
                                                             fieldname)
        if self.ifdef is not None:
            yield '#else'
            yield 'dump("defined", 0);'
            yield '#endif'

    def build_result(self, info, config_result):
        if self.ifdef is not None:
            if not info['defined']:
                return None
        alignment = 1
        layout = [None] * info['size']
        for fieldname, fieldtype in self.interesting_fields:
            if isinstance(fieldtype, Struct):
                offset = info['fldofs '  + fieldname]
                size   = info['fldsize ' + fieldname]
                c_fieldtype = config_result.get_entry_result(fieldtype)
                layout_addfield(layout, offset, c_fieldtype, fieldname)
                alignment = max(alignment, ctype_alignment(c_fieldtype))
            else:
                offset = info['fldofs '  + fieldname]
                size   = info['fldsize ' + fieldname]
                sign   = info.get('fldunsigned ' + fieldname, False)
                if (size, sign) != size_and_sign(fieldtype):
                    fieldtype = fixup_ctype(fieldtype, fieldname, (size, sign))
                layout_addfield(layout, offset, fieldtype, fieldname)
                alignment = max(alignment, ctype_alignment(fieldtype))

        # try to enforce the same alignment as the one of the original
        # structure
        if alignment < info['align']:
            choices = [ctype for ctype in alignment_types
                             if ctype_alignment(ctype) == info['align']]
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
        name = self.name
        if name.startswith('struct '):
            name = name[7:]
        S.__name__ = name
        return S


class SimpleType(CConfigEntry):
    """An entry in a CConfig class that stands for an externally
    defined simple numeric type.
    """
    def __init__(self, name, ctype_hint=ctypes.c_int, ifdef=None):
        self.name = name
        self.ctype_hint = ctype_hint
        self.ifdef = ifdef
        
    def prepare_code(self):
        if self.ifdef is not None:
            yield '#ifdef %s' % (self.ifdef,)
        yield 'typedef %s ctypesplatcheck_t;' % (self.name,)
        yield ''
        yield 'ctypesplatcheck_t x;'
        if self.ifdef is not None:
            yield 'dump("defined", 1);'
        yield 'dump("size",  sizeof(ctypesplatcheck_t));'
        if self.ctype_hint in integer_class:
            yield 'x = 0; x = ~x;'
            yield 'dump("unsigned", x > 0);'
        if self.ifdef is not None:
            yield '#else'
            yield 'dump("defined", 0);'
            yield '#endif'

    def build_result(self, info, config_result):
        if self.ifdef is not None and not info['defined']:
            return None
        size = info['size']
        sign = info.get('unsigned', False)
        ctype = self.ctype_hint
        if (size, sign) != size_and_sign(ctype):
            ctype = fixup_ctype(ctype, self.name, (size, sign))
        return ctype


class ConstantInteger(CConfigEntry):
    """An entry in a CConfig class that stands for an externally
    defined integer constant.
    """
    def __init__(self, name):
        self.name = name

    def prepare_code(self):
        yield 'if ((%s) < 0) {' % (self.name,)
        yield '    long long x = (long long)(%s);' % (self.name,)
        yield '    printf("value: %lld\\n", x);'
        yield '} else {'
        yield '    unsigned long long x = (unsigned long long)(%s);' % (
                        self.name,)
        yield '    printf("value: %llu\\n", x);'
        yield '}'

    def build_result(self, info, config_result):
        return info['value']

class DefinedConstantInteger(CConfigEntry):
    """An entry in a CConfig class that stands for an externally
    defined integer constant. If not #defined the value will be None.
    """
    def __init__(self, macro):
        self.name = self.macro = macro

    def prepare_code(self):
        yield '#ifdef %s' % self.macro
        yield 'dump("defined", 1);'
        yield 'if ((%s) < 0) {' % (self.macro,)
        yield '    long long x = (long long)(%s);' % (self.macro,)
        yield '    printf("value: %lld\\n", x);'
        yield '} else {'
        yield '    unsigned long long x = (unsigned long long)(%s);' % (
                        self.macro,)
        yield '    printf("value: %llu\\n", x);'
        yield '}'
        yield '#else'
        yield 'dump("defined", 0);'
        yield '#endif'

    def build_result(self, info, config_result):
        if info["defined"]:
            return info['value']
        return None


class DefinedConstantString(CConfigEntry):
    """
    """
    def __init__(self, macro):
        self.macro = macro
        self.name = macro

    def prepare_code(self):
        yield '#ifdef %s' % self.macro
        yield 'int i;'
        yield 'char *p = %s;' % self.macro
        yield 'dump("defined", 1);'
        yield 'for (i = 0; p[i] != 0; i++ ) {'
        yield '  printf("value_%d: %d\\n", i, (int)(unsigned char)p[i]);'
        yield '}'
        yield '#else'
        yield 'dump("defined", 0);'
        yield '#endif'

    def build_result(self, info, config_result):
        if info["defined"]:
            string = ''
            d = 0
            while info.has_key('value_%d' % d):
                string += chr(info['value_%d' % d])
                d += 1
            return string
        return None


class Defined(CConfigEntry):
    """A boolean, corresponding to an #ifdef.
    """
    def __init__(self, macro):
        self.macro = macro
        self.name = macro

    def prepare_code(self):
        yield '#ifdef %s' % (self.macro,)
        yield 'dump("defined", 1);'
        yield '#else'
        yield 'dump("defined", 0);'
        yield '#endif'

    def build_result(self, info, config_result):
        return bool(info['defined'])

class CConfigSingleEntry(object):
    """ An abstract class of type which requires
    gcc succeeding/failing instead of only asking
    """
    pass

class Has(CConfigSingleEntry):
    def __init__(self, name):
        self.name = name
    
    def question(self, ask_gcc):
        return ask_gcc(self.name + ';')

class Works(CConfigSingleEntry):
    def question(self, ask_gcc):
        return ask_gcc("")

class SizeOf(CConfigEntry):
    """An entry in a CConfig class that stands for
    some external opaque type
    """
    def __init__(self, name):
        self.name = name

    def prepare_code(self):
        yield 'dump("size",  sizeof(%s));' % self.name

    def build_result(self, info, config_result):
        return info['size']

# ____________________________________________________________
#
# internal helpers

def ctype_alignment(c_type):
    if issubclass(c_type, ctypes.Structure):
        return max([ctype_alignment(fld_type)
                     for fld_name, fld_type in c_type._fields_])
    
    return ctypes.alignment(c_type)

def uniquefilepath(LAST=[0]):
    i = LAST[0]
    LAST[0] += 1
    return configdir.join('ctypesplatcheck_%d.c' % i)

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
    if (hasattr(fieldtype, '_length_')
        and getattr(fieldtype, '_type_', None) == ctypes.c_char):
        # for now, assume it is an array of chars; otherwise we'd also
        # have to check the exact integer type of the elements of the array
        size, sign = expected_size_and_sign
        return ctypes.c_char * size
    if (hasattr(fieldtype, '_length_')
        and getattr(fieldtype, '_type_', None) == ctypes.c_ubyte):
        # grumble, fields of type 'c_char array' have automatic cast-to-
        # Python-string behavior in ctypes, which may not be what you
        # want, so here is the same with c_ubytes instead...
        size, sign = expected_size_and_sign
        return ctypes.c_ubyte * size
    raise TypeError("conflicting field type %r for %r" % (fieldtype,
                                                          fieldname))


C_HEADER = """
#include <stdio.h>
#include <stddef.h>   /* for offsetof() */

void dump(char* key, int value) {
    printf("%s: %d\\n", key, value);
}
"""

def run_example_code(filepath, eci):
    executable = build_executable([filepath], eci)
    output = py.process.cmdexec(executable)
    section = None
    for line in output.splitlines():
        line = line.strip()
        if line.startswith('-+- '):      # start of a new section
            section = {}
        elif line == '---':              # section end
            assert section is not None
            yield section
            section = None
        elif line:
            assert section is not None
            key, value = line.split(': ')
            section[key] = int(value)

# ____________________________________________________________

def get_python_include_dir():
    from distutils import sysconfig
    gcv = sysconfig.get_config_vars()
    return gcv['INCLUDEPY']

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
    else:
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
