# nightly test configuration for the paraller runner
import os

DIRS_SPLIT = [
    'translator/c', 'translator/jvm', 'rlib', 'rpython/memory',
    'jit/backend/x86', 'jit/metainterp', 'rpython/test',
]

def collect_one_testdir(testdirs, reldir, tests):
    for dir in DIRS_SPLIT:
        if reldir.startswith(dir):
            testdirs.extend(tests)
            break
    else:
        testdirs.append(reldir)


_cherrypick = os.getenv('PYPYCHERRYPICK', '')
if _cherrypick:
    cherrypick = _cherrypick.split(':')
