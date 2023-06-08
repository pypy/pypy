import sys
import importlib
import pytest

# This is a workaround for a dubious feature of CPython's test suite: it skips
# tests silently if importing a module fails.  This makes some partial sense
# for CPython itself when testing C extension modules directly, because very
# often (but not always) a C extension module is either completely absent or
# imports successfully.  But for PyPy it's a mess because it can hide mistakes
# very easily, and it did.  So the list we build here should contain the names
# of every module that CPython's tests import with test.support.import_module()
# but that should really be present on the running platform.


expected_modules = []

# ----- everywhere -----
expected_modules += [
    'MimeWriter',
    'bz2',
    'commands',
    'compiler',
    '_ctypes',
    'dircache',
    'fpformat',
    'gzip',
    'htmllib',
    'mhlib',
    'mimetools',
    'mmap',
    'multifile',
    '_multiprocessing',
    'multiprocessing.synchronize',
    'mutex',
    'new',
    'sre',
    'rfc822',
    'sets',
    '_sqlite3',
    'ssl',
    'thread',
    'threading',
    'xmllib',
    'zlib',
]

# ----- non-Windows -----
if sys.platform != 'win32':
    expected_modules += [
        'curses',
        'curses.ascii',
        'curses.textpad',
        'dbm',
        'fcntl',
        'gdbm',
        'grp',
        'posix',
        'pwd',
        'readline',
        'resource',
        'termios',
    ]
else:
    # ----- Windows only -----
    expected_modules += [
        '_winreg',
    ]

# ----- Linux only -----
if sys.platform.startswith('linux'):
    expected_modules += [
        'crypt',
    ]


# ------------------------------------------------

@pytest.fixture(scope="module", params=expected_modules)
def modname(request):
    return request.param

def test_expected_modules(modname):
    importlib.import_module(modname)
