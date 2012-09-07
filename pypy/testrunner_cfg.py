# nightly test configuration for the paraller runner
import os
import platform

# manually set variables to force some specific form of machine based collection
_ARM = platform.machine().startswith('arm')
_X86 = platform.machine().startswith('x86')

DIRS_SPLIT = [
    'translator/c', 'translator/jvm', 'rlib',
    'rpython/memory', 'jit/metainterp', 'rpython/test',
]
backend_tests = {'arm':'jit/backend/arm', 'x86':'jit/backend/x86'}

def add_backend_tests():
    l = []
    if _ARM:
        l.append('arm')
    if _X86: # X86 for now, adapt as required for PPC
        l.append('x86')
    for i in l:
        if backend_tests[i] in DIRS_SPLIT:
            continue
        DIRS_SPLIT.append(backend_tests[i])

def collect_one_testdir(testdirs, reldir, tests):
    add_backend_tests()
    for dir in DIRS_SPLIT:
        if reldir.startswith(dir):
            testdirs.extend(tests)
            break
    else:
        testdirs.append(reldir)


_cherrypick = os.getenv('PYPYCHERRYPICK', '')
if _cherrypick:
    cherrypick = _cherrypick.split(':')
