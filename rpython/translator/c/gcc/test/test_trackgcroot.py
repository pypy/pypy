import py
import sys, re
from rpython.translator.c.gcc.trackgcroot import LOC_NOWHERE, LOC_REG
from rpython.translator.c.gcc.trackgcroot import LOC_EBP_PLUS, LOC_EBP_MINUS
from rpython.translator.c.gcc.trackgcroot import LOC_ESP_PLUS
from rpython.translator.c.gcc.trackgcroot import ElfAssemblerParser
from rpython.translator.c.gcc.trackgcroot import DarwinAssemblerParser
from rpython.translator.c.gcc.trackgcroot import PARSERS
from rpython.translator.c.gcc.trackgcroot import ElfFunctionGcRootTracker32
from StringIO import StringIO
import py.test

this_dir = py.path.local(__file__).dirpath()


def test_format_location():
    cls = ElfFunctionGcRootTracker32
    assert cls.format_location(LOC_NOWHERE) == '?'
    assert cls.format_location(LOC_REG | (1<<2)) == '%ebx'
    assert cls.format_location(LOC_REG | (2<<2)) == '%esi'
    assert cls.format_location(LOC_REG | (3<<2)) == '%edi'
    assert cls.format_location(LOC_REG | (4<<2)) == '%ebp'
    assert cls.format_location(LOC_EBP_PLUS + 0) == '(%ebp)'
    assert cls.format_location(LOC_EBP_PLUS + 4) == '4(%ebp)'
    assert cls.format_location(LOC_EBP_MINUS + 4) == '-4(%ebp)'
    assert cls.format_location(LOC_ESP_PLUS + 0) == '(%esp)'
    assert cls.format_location(LOC_ESP_PLUS + 4) == '4(%esp)'

def test_format_callshape():
    cls = ElfFunctionGcRootTracker32
    expected = ('{4(%ebp) '               # position of the return address
                '| 8(%ebp), 12(%ebp), 16(%ebp), 20(%ebp) '  # 4 saved regs
                '| 24(%ebp), 28(%ebp)}')                    # GC roots
    assert cls.format_callshape((LOC_EBP_PLUS+4,
                                 LOC_EBP_PLUS+8,
                                 LOC_EBP_PLUS+12,
                                 LOC_EBP_PLUS+16,
                                 LOC_EBP_PLUS+20,
                                 LOC_EBP_PLUS+24,
                                 LOC_EBP_PLUS+28)) == expected

def test_compress_callshape():
    cls = ElfFunctionGcRootTracker32
    shape = (1, 127, 0x1234, 0x5678, 0x234567,
             0x765432, 0x61626364, 0x41424344)
    bytes = list(cls.compress_callshape(shape))
    print bytes
    assert len(bytes) == 1+1+2+3+4+4+5+5+1
    assert cls.decompress_callshape(bytes) == list(shape)

def test_find_functions_elf():
    source = """\
\t.p2align 4,,15
.globl pypy_g_make_tree
\t.type\tpypy_g_make_tree, @function
\tFOO
\t.size\tpypy_g_make_tree, .-pypy_g_make_tree

\t.p2align 4,,15
.globl pypy_fn2
\t.type\tpypy_fn2, @function
\tBAR
\t.size\tpypy_fn2, .-pypy_fn2
\tMORE STUFF
"""
    lines = source.splitlines(True)
    parts = list(ElfAssemblerParser().find_functions(iter(lines)))
    assert len(parts) == 5
    assert parts[0] == (False, lines[:2])
    assert parts[1] == (True,  lines[2:5])
    assert parts[2] == (False, lines[5:8])
    assert parts[3] == (True,  lines[8:11])
    assert parts[4] == (False, lines[11:])

def test_find_functions_darwin():
    source = """\
\t.text
\t.align 4,0x90
.globl _pypy_g_ll_str__StringR_Ptr_GcStruct_rpy_strin_rpy_strin
_pypy_g_ll_str__StringR_Ptr_GcStruct_rpy_strin_rpy_strin:
L0:
\tFOO
\t.align 4,0x90
_static:
\tSTATIC
\t.align 4,0x90
.globl _pypy_g_ll_issubclass__object_vtablePtr_object_vtablePtr
_pypy_g_ll_issubclass__object_vtablePtr_object_vtablePtr:
\tBAR
\t.cstring
\t.ascii "foo"
\t.text
\t.align 4,0x90
.globl _pypy_g_RPyRaiseException
_pypy_g_RPyRaiseException:
\tBAZ
\t.section stuff
"""
    lines = source.splitlines(True)
    parts = list(DarwinAssemblerParser().find_functions(iter(lines)))
    assert len(parts) == 6
    assert parts[0] == (False, lines[:3])
    assert parts[1] == (True,  lines[3:7])
    assert parts[2] == (True,  lines[7:11])
    assert parts[3] == (True,  lines[11:18])
    assert parts[4] == (True,  lines[18:20])
    assert parts[5] == (False, lines[20:])
 
def test_computegcmaptable():
    tests = []
    for format in ('elf', 'elf64', 'darwin', 'darwin64', 'msvc'):
        for path in this_dir.join(format).listdir("track*.s"):
            n = path.purebasename[5:]
            try:
                n = int(n)
            except ValueError:
                pass
            tests.append((format, n, path))
    tests.sort()
    for format, _, path in tests:
        yield check_computegcmaptable, format, path


r_expected        = re.compile(r"\s*;;\s*expected\s+([{].+[}])")
r_gcroot_constant = re.compile(r";\tmov\t.+, .+_constant_always_one_")

def check_computegcmaptable(format, path):
    if format == 'msvc':
        r_globallabel = re.compile(r"([\w]+)::")
    elif format == 'darwin' or format == 'darwin64':
        py.test.skip("disabled on OS/X's terribly old gcc")
    else:
        r_globallabel = re.compile(r"([\w]+)=[.]+")
    print
    print path.dirpath().basename + '/' + path.basename
    lines = path.readlines()
    expectedlines = lines[:]
    tracker = PARSERS[format].FunctionGcRootTracker(lines)
    table = tracker.computegcmaptable(verbose=sys.maxint)
    tabledict = {}
    seen = {}
    for entry in table:
        print '%s: %s' % (entry[0], tracker.format_callshape(entry[1]))
        tabledict[entry[0]] = entry[1]
    # find the ";; expected" lines
    prevline = ""
    for i, line in enumerate(lines):
        match = r_expected.match(line)
        if match:
            expected = match.group(1)
            prevmatch = r_globallabel.match(prevline)
            assert prevmatch, "the computed table is not complete"
            label = prevmatch.group(1)
            assert label in tabledict
            got = tabledict[label]
            assert tracker.format_callshape(got) == expected
            seen[label] = True
            if format == 'msvc':
                expectedlines.insert(i-2, 'PUBLIC\t%s\n' % (label,))
                expectedlines.insert(i-1, '%s::\n' % (label,))
            else:
                expectedlines.insert(i-2, '\t.globl\t%s\n' % (label,))
                expectedlines.insert(i-1, '%s=.+%d\n' % (label,
                                                         tracker.OFFSET_LABELS))
        if format == 'msvc' and r_gcroot_constant.match(line):
            expectedlines[i] = ';' + expectedlines[i]
            expectedlines[i+1] = (expectedlines[i+1]
                                  .replace('\timul\t', '\tmov\t')
                                  + '\t; GCROOT\n')
        prevline = line
    assert len(seen) == len(tabledict), (
        "computed table contains unexpected entries:\n%r" %
        [key for key in tabledict if key not in seen])
    print '--------------- got ---------------'
    print ''.join(lines)
    print '------------- expected ------------'
    print ''.join(expectedlines)
    print '-----------------------------------'
    assert lines == expectedlines
