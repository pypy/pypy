# Adapted from cpython Tools/scripts/generate_stdlib_module_names.py

import os
from pypy import pypydir

STDLIB_PATH = os.path.join(pypydir, '..', 'lib-python', '3')

IGNORE = {
    '__init__',
    '__pycache__',
    'site-packages',

    # Test modules and packages
    '__hello__',
    '__phello__',
    '_ctypes_test',
    '_testbuffer',
    '_testcapi',
    '_testconsole',
    '_testimportmultiple',
    '_testinternalcapi',
    '_testmultiphase',
    '_xxsubinterpreters',
    '_xxtestfuzz',
    'distutils.tests',
    'idlelib.idle_test',
    'lib2to3.tests',
    'test',
    'xxlimited',
    'xxlimited_35',
    'xxsubtype',
}

# Windows extension modules
WINDOWS_MODULES = (
    '_msi',
    '_overlapped',
    '_testconsole',
    '_winapi',
    'msvcrt',
    'nt',
    'winreg',
    'winsound'
)

# macOS extension modules
MACOS_MODULES = (
    '_scproxy',
)

LIB_PYPY_MODULES = (
    'audioop',
    '_codecs_cn',
    '_codecs_hk',
    '_codecs_iso2022',
    '_codecs_jp',
    '_codecs_kr',
    '_codecs_tw',
    '_collections',
    '_contextvars',
    'ctypes_support',
    '_curses_panel',
    '_curses',
    '_dbm',
    # '_decimal.py', # issue 3024
    'faulthandler',
    '_ffi',
    'future_builtins',
    '_gdbm',
    'greenlet',
    'grp',
    'identity_dict',
    '_immutables_map',
    '__init__',
    '_lzma',
    '_marshal',
    'marshal',
    '_md5',
    'msvcrt',
    '_overlapped',
    '_posixshmem',
    '_pypy_generic_alias',
    '_pypy_interact',
    '_pypy_irc_topic',
    '_pypy_util_cffi',
    '_pypy_wait',
    '_pypy_winbase_cffi64',
    '_pypy_winbase_cffi',
    'readline',
    'resource',
    '_scproxy',
    '_sha1',
    '_sha256',
    '_sha512',
    '_sqlite3',
    'stackless',
    '_structseq',
    '_sysconfigdata',
    'syslog',
    '_testcapi',
    'tputil',
    '_winapi',
)


# Pure Python modules (Lib/*.py)
def list_python_modules(names):
    for filename in os.listdir(STDLIB_PATH):
        if not filename.endswith(".py"):
            continue
        name = filename[:-3]
        names.add(name)


# Packages in Lib/
def list_packages(names):
    for name in os.listdir(STDLIB_PATH):
        if name in IGNORE:
            continue
        package_path = os.path.join(STDLIB_PATH, name)
        if not os.path.isdir(package_path):
            continue
        if any(package_file.endswith(".py")
               for package_file in os.listdir(package_path)):
            names.add(name)


# extension modules built by build_cffi_imports
def list_modules_cffi(names):
    for name in LIB_PYPY_MODULES:
        names.add(name)


def list_modules():
    names = set(WINDOWS_MODULES) | set(MACOS_MODULES)
    list_modules_cffi(names)
    list_packages(names)
    list_python_modules(names)

    # Remove ignored packages and modules
    for name in list(names):
        package_name = name.split('.')[0]
        # package_name can be equal to name
        if package_name in IGNORE:
            names.discard(name)

    for name in names:
        if "." in name:
            raise Exception("sub-module '%s' must not be listed" % name)

    return names


def get_stdlib_names():
    return list(list_modules())


if __name__ == "__main__":
    import pprint
    modules = get_stdlib_names()
    pprint.pprint(modules)
    print('got %d modules' % len(modules))
