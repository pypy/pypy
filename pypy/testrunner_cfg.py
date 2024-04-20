# nightly test configuration for the paraller runner
import os

DIRS_SPLIT = [
    'translator/c', 'rlib',
    'memory/test', 'jit/metainterp',
    'jit/backend/aarch64', 
    'jit/backend/x86',
    'module/cpyext/test',
    'module/_hpy_universal/test/_vendored',
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
