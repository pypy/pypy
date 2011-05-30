# nightly test configuration for the paraller runner
import os

def collect_one_testdir(testdirs, reldir, tests):
    if (reldir.startswith('translator/c/') or 
        reldir.startswith('translator/jvm/') or
        reldir.startswith('rlib/test') or
        reldir.startswith('rpython/memory/') or
        reldir.startswith('jit/backend/x86/') or
        #reldir.startswith('jit/backend/cli') or
        0):
        testdirs.extend(tests)
    else:
        testdirs.append(reldir)


_cherrypick = os.getenv('PYPYCHERRYPICK', '')
if _cherrypick:
    cherrypick = _cherrypick.split(':')
