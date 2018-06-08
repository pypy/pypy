import _imp
import os
import sys
from distutils.spawn import find_executable

so_ext = _imp.extension_suffixes()[0]


build_time_vars = {
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
    'LIBDIR': os.path.join(sys.prefix, 'lib'),
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

