import _imp
import os
import sys
from distutils.spawn import find_executable

so_ext = _imp.extension_suffixes()[0]


build_time_vars = {
    # SOABI is PEP 3149 compliant, but CPython3 has so_ext.split('.')[1]
    # ("ABI tag"-"platform tag") where this is ABI tag only. Wheel 0.34.2
    # depends on this value, so don't make it CPython compliant without
    # checking wheel: it uses pep425tags.get_abi_tag with special handling
    # for CPython
    "SOABI": '-'.join(so_ext.split('.')[1].split('-')[:2]),
    "SO": so_ext,  # deprecated in Python 3, for backward compatibility
    'CC': "cc -pthread",
    'CXX': "c++ -pthread",
    'OPT': "-DNDEBUG -O2",
    'CFLAGS': "-DNDEBUG -O2",
    'CCSHARED': "-fPIC",
    'LDSHARED': "cc -pthread -shared",
    'EXT_SUFFIX': so_ext,
    'SHLIB_SUFFIX': ".so",
    'AR': "ar",
    'ARFLAGS': "rc",
    'EXE': "",
    'LIBDIR': os.path.join(sys.prefix, 'bin'),
    'VERSION': sys.version[:3]
}

if find_executable("gcc"):
    build_time_vars.update({
        "CC": "gcc -pthread",
        "GNULD": "yes",
        "LDSHARED": "gcc -pthread -shared",
    })
    if find_executable("g++"):
        build_time_vars["CXX"] = "g++ -pthread"

if sys.platform[:6] == "darwin":
    import platform
    if platform.machine() == 'i386':
        if platform.architecture()[0] == '32bit':
            arch = 'i386'
        else:
            arch = 'x86_64'
    else:
        # just a guess
        arch = platform.machine()
    build_time_vars['LDSHARED'] += ' -undefined dynamic_lookup'
    build_time_vars['CC'] += ' -arch %s' % (arch,)
    if "CXX" in build_time_vars:
        build_time_vars['CXX'] += ' -arch %s' % (arch,)
    build_time_vars['MACOSX_DEPLOYMENT_TARGET'] = '10.7'

