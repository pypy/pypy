import py
import sys, re
from pypy.translator.c.gcc.trackgcroot import format_location
from pypy.translator.c.gcc.trackgcroot import format_callshape
from pypy.translator.c.gcc.trackgcroot import LOC_NOWHERE, LOC_REG
from pypy.translator.c.gcc.trackgcroot import LOC_EBP_BASED, LOC_ESP_BASED
from pypy.translator.c.gcc.trackgcroot import GcRootTracker
from pypy.translator.c.gcc.trackgcroot import FunctionGcRootTracker
from pypy.translator.c.gcc.trackgcroot import compress_callshape
from pypy.translator.c.gcc.trackgcroot import decompress_callshape
from StringIO import StringIO

this_dir = py.path.local(__file__).dirpath()


def test_format_location():
    assert format_location(LOC_NOWHERE) == '?'
    assert format_location(LOC_REG | (0<<2)) == '%ebx'
    assert format_location(LOC_REG | (1<<2)) == '%esi'
    assert format_location(LOC_REG | (2<<2)) == '%edi'
    assert format_location(LOC_REG | (3<<2)) == '%ebp'
    assert format_location(LOC_EBP_BASED + 0) == '(%ebp)'
    assert format_location(LOC_EBP_BASED + 4) == '4(%ebp)'
    assert format_location(LOC_EBP_BASED - 4) == '-4(%ebp)'
    assert format_location(LOC_ESP_BASED + 0) == '(%esp)'
    assert format_location(LOC_ESP_BASED + 4) == '4(%esp)'
    assert format_location(LOC_ESP_BASED - 4) == '-4(%esp)'

def test_format_callshape():
    expected = ('{4(%ebp) '               # position of the return address
                '| 8(%ebp), 12(%ebp), 16(%ebp), 20(%ebp) '  # 4 saved regs
                '| 24(%ebp), 28(%ebp)}')                    # GC roots
    assert format_callshape((LOC_EBP_BASED+4,
                             LOC_EBP_BASED+8,
                             LOC_EBP_BASED+12,
                             LOC_EBP_BASED+16,
                             LOC_EBP_BASED+20,
                             LOC_EBP_BASED+24,
                             LOC_EBP_BASED+28)) == expected

def test_compress_callshape():
    shape = (1, -3, 0x1234, -0x5678, 0x234567,
             -0x765432, 0x61626364, -0x41424344)
    bytes = list(compress_callshape(shape))
    print bytes
    assert len(bytes) == 1+1+2+3+4+4+5+5+1
    assert decompress_callshape(bytes) == list(shape)

def test_find_functions():
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
    parts = list(GcRootTracker().find_functions(iter(lines)))
    assert len(parts) == 5
    assert parts[0] == (False, lines[:2])
    assert parts[1] == (True,  lines[2:5])
    assert parts[2] == (False, lines[5:8])
    assert parts[3] == (True,  lines[8:11])
    assert parts[4] == (False, lines[11:])


def test_computegcmaptable():
    tests = []
    for path in this_dir.listdir("track*.s"):
        n = path.purebasename[5:]
        try:
            n = int(n)
        except ValueError:
            pass
        tests.append((n, path))
    tests.sort()
    for _, path in tests:
        yield check_computegcmaptable, path

r_globallabel = re.compile(r"([\w]+)[:]")
r_expected = re.compile(r"\s*;;\s*expected\s+([{].+[}])")

def check_computegcmaptable(path):
    print
    print path.basename
    lines = path.readlines()
    expectedlines = lines[:]
    tracker = FunctionGcRootTracker(lines)
    table = tracker.computegcmaptable(verbose=sys.maxint)
    tabledict = {}
    seen = {}
    for entry in table:
        print '%s: %s' % (entry[0], format_callshape(entry[1]))
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
            assert format_callshape(got) == expected
            seen[label] = True
            expectedlines.insert(i-2, '\t.globl\t%s\n' % (label,))
            expectedlines.insert(i-1, '%s:\n' % (label,))
        prevline = line
    assert len(seen) == len(tabledict), (
        "computed table contains unexpected entries:\n%r" %
        [key for key in tabledict if key not in seen])
    assert lines == expectedlines
