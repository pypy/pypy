# nightly test configuration for the paraller runner
import os

DIRS_SPLIT = [
    'translator/c', 'rlib',
    'memory/test', 'jit/metainterp',
    'jit/backend/arm', 'jit/backend/x86',
    'jit/backend/zarch',
]

def collect_one_testdir(testdirs, reldir, tests):
    if reldir.startswith('module/faulthandler'):
        testdirs.append(reldir)


_cherrypick = os.getenv('PYPYCHERRYPICK', '')
if _cherrypick:
    cherrypick = _cherrypick.split(':')
