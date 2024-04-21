# nightly test configuration for the paraller runner
import os
import platform
import sys

IS_ARM64 = platform.machine() == 'arm64'
IS_MACOS = sys.platform == 'darwin'
IS_PYPY = 'pypyjit' in sys.builtin_module_names
IS_PYPY_MACOS_ARM64 = IS_ARM64 and IS_MACOS and IS_PYPY

DIRS_SPLIT = [
    'translator/c', 'rlib',
    'memory/test', 'jit/metainterp',
    'jit/backend/aarch64', 
    'jit/backend/x86',
    'module/cpyext/test',
    'module/_hpy_universal/test/_vendored',
]

pytestpath = os.path.abspath('pytest.py')

def collect_one_testdir(testdirs, reldir, tests):
    for dir in DIRS_SPLIT:
        if reldir.startswith(dir):
            testdirs.extend(tests)
            break
    else:
        testdirs.append(reldir)

def get_test_driver(testdir):
    if "jit/backend/aarch64" in testdir and IS_PYPY_MACOS_ARM64:
        return ["--jit", "off",  pytestpath]
    return [pytestpath]

_cherrypick = os.getenv('PYPYCHERRYPICK', '')
if _cherrypick:
    cherrypick = _cherrypick.split(':')
