"""Provide access to Python's configuration information.
This is actually PyPy's minimal configuration information.

The specific configuration variables available depend heavily on the
platform and configuration.  The values may be retrieved using
get_config_var(name), and the list of variables is available via
get_config_vars().keys().  Additional convenience functions are also
available.
"""

import sys
import os
import imp

from distutils.errors import DistutilsPlatformError


PREFIX = os.path.normpath(sys.prefix)
EXEC_PREFIX = os.path.normpath(sys.exec_prefix)
project_base = os.path.dirname(os.path.abspath(sys.executable))
python_build = False


def get_python_inc(plat_specific=0, prefix=None):
    """Return the directory containing installed Python header files.

    If 'plat_specific' is false (the default), this is the path to the
    non-platform-specific header files, i.e. Python.h and so on;
    otherwise, this is the path to platform-specific header files
    (namely pyconfig.h). These are identical on PyPy.

    If 'prefix' is supplied, use it.
    """
    if prefix is None:
        # PyPy extension to try base_prefix (if inside virtualenv)
        prefix = getattr(sys, 'base_prefix', sys.prefix)

    return os.path.join(prefix, 'include')

def get_python_version():
    """Return a string containing the major and minor Python version,
    leaving off the patchlevel.  Sample return values could be '1.5'
    or '2.2'.
    """
    return sys.version[:3]


def get_python_lib(plat_specific=0, standard_lib=0, prefix=None):
    """Return the directory containing the Python library (standard or
    site additions).

    If 'plat_specific' is true, return the directory containing
    platform-specific modules, i.e. any module from a non-pure-Python
    module distribution; otherwise, return the platform-shared library
    directory.  If 'standard_lib' is true, return the directory
    containing standard Python library modules; otherwise, return the
    directory for site-specific modules.

    If 'prefix' is supplied, use it instead of sys.prefix or
    sys.exec_prefix -- i.e., ignore 'plat_specific'.
    """
    if prefix is None:
        prefix = PREFIX
    if standard_lib:
        return os.path.join(prefix, "lib-python", get_python_version())
    return os.path.join(prefix, 'site-packages')


_config_vars = None

def _init_posix():
    """Initialize the module as appropriate for POSIX systems."""
    g = {}
    g['CC'] = "cc -pthread"
    g['CXX'] = "c++ -pthread"
    g['OPT'] = "-DNDEBUG -O2"
    g['CFLAGS'] = "-DNDEBUG -O2"
    g['CCSHARED'] = "-fPIC"
    g['LDSHARED'] = "cc -pthread -shared"
    g['SO'] = [s[0] for s in imp.get_suffixes() if s[2] == imp.C_EXTENSION][0]
    g['AR'] = "ar"
    g['ARFLAGS'] = "rc"
    g['EXE'] = ""
    g['LIBDIR'] = os.path.join(sys.prefix, 'bin') # where is the shared library
    g['VERSION'] = get_python_version()

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
        g['LDSHARED'] += ' -undefined dynamic_lookup'
        g['CC'] += ' -arch %s' % (arch,)
        g['MACOSX_DEPLOYMENT_TARGET'] = '10.7'

    # pypy only: give us control over the ABI tag in a wheel name
    if '__pypy__' in sys.builtin_module_names:
        for suffix, mode, type_ in imp.get_suffixes():
            if type_ == imp.C_EXTENSION:
                g['SOABI'] = suffix.split('.')[1]
                break

    global _config_vars
    _config_vars = g


def _init_nt():
    """Initialize the module as appropriate for NT"""
    g = {}
    g['EXE'] = ".exe"
    g['SO'] = [s[0] for s in imp.get_suffixes() if s[2] == imp.C_EXTENSION][0]
    g['VERSION'] = get_python_version().replace(".", "")
    g['BINDIR'] = os.path.dirname(os.path.abspath(sys.executable))

    # pypy only: give us control over the ABI tag in a wheel name
    if '__pypy__' in sys.builtin_module_names:
        so_ext = imp.get_suffixes()[0][0]
        g['SOABI']= '-'.join(so_ext.split('.')[1].split('-')[:2])

    global _config_vars
    _config_vars = g


def get_config_vars(*args):
    """With no arguments, return a dictionary of all configuration
    variables relevant for the current platform.  Generally this includes
    everything needed to build extensions and install both pure modules and
    extensions.  On Unix, this means every variable defined in Python's
    installed Makefile; on Windows and Mac OS it's a much smaller set.

    With arguments, return a list of values that result from looking up
    each argument in the configuration variable dictionary.
    """
    global _config_vars
    if _config_vars is None:
        func = globals().get("_init_" + os.name)
        if func:
            func()
        else:
            _config_vars = {}

        _config_vars['prefix'] = PREFIX
        _config_vars['exec_prefix'] = EXEC_PREFIX

        # OS X platforms require special customization to handle
        # multi-architecture, multi-os-version installers
        if sys.platform == 'darwin':
            import _osx_support
            _osx_support.customize_config_vars(_config_vars)

    if args:
        vals = []
        for name in args:
            vals.append(_config_vars.get(name))
        return vals
    else:
        return _config_vars

def get_config_var(name):
    """Return the value of a single variable using the dictionary
    returned by 'get_config_vars()'.  Equivalent to
    get_config_vars().get(name)
    """
    return get_config_vars().get(name)


def customize_compiler(compiler):
    """Do any platform-specific customization of a CCompiler instance.

    Mainly needed on Unix, so we can plug in the information that
    varies across Unices and is stored in Python's Makefile (CPython)
    or hard-coded in _init_posix() (PyPy).
    """
    if compiler.compiler_type == "unix":
        if sys.platform == "darwin":
            # Perform first-time customization of compiler-related
            # config vars on OS X now that we know we need a compiler.
            # This is primarily to support Pythons from binary
            # installers.  The kind and paths to build tools on
            # the user system may vary significantly from the system
            # that Python itself was built on.  Also the user OS
            # version and build tools may not support the same set
            # of CPU architectures for universal builds.
            global _config_vars
            # Use get_config_var() to ensure _config_vars is initialized.
            if not get_config_var('CUSTOMIZED_OSX_COMPILER'):
                import _osx_support
                _osx_support.customize_compiler(_config_vars)
                _config_vars['CUSTOMIZED_OSX_COMPILER'] = 'True'

        (cc, cxx, opt, cflags, ccshared, ldshared, so_ext, ar, ar_flags) = \
            get_config_vars('CC', 'CXX', 'OPT', 'CFLAGS',
                            'CCSHARED', 'LDSHARED', 'SO', 'AR',
                            'ARFLAGS')

        if 'CC' in os.environ:
            newcc = os.environ['CC']
            if (sys.platform == 'darwin'
                    and 'LDSHARED' not in os.environ
                    and ldshared.startswith(cc)):
                # On OS X, if CC is overridden, use that as the default
                #       command for LDSHARED as well
                ldshared = newcc + ldshared[len(cc):]
            cc = newcc
        if 'CXX' in os.environ:
            cxx = os.environ['CXX']
        if 'LDSHARED' in os.environ:
            ldshared = os.environ['LDSHARED']
        if 'CPP' in os.environ:
            cpp = os.environ['CPP']
        else:
            cpp = cc + " -E"           # not always
        if 'LDFLAGS' in os.environ:
            ldshared = ldshared + ' ' + os.environ['LDFLAGS']
        if 'CFLAGS' in os.environ:
            cflags = opt + ' ' + os.environ['CFLAGS']
            ldshared = ldshared + ' ' + os.environ['CFLAGS']
        if 'CPPFLAGS' in os.environ:
            cpp = cpp + ' ' + os.environ['CPPFLAGS']
            cflags = cflags + ' ' + os.environ['CPPFLAGS']
            ldshared = ldshared + ' ' + os.environ['CPPFLAGS']
        if 'AR' in os.environ:
            ar = os.environ['AR']
        if 'ARFLAGS' in os.environ:
            archiver = ar + ' ' + os.environ['ARFLAGS']
        else:
            archiver = ar + ' ' + ar_flags

        cc_cmd = cc + ' ' + cflags
        compiler.set_executables(
            preprocessor=cpp,
            compiler=cc_cmd,
            compiler_so=cc_cmd + ' ' + ccshared,
            compiler_cxx=cxx,
            linker_so=ldshared,
            linker_exe=cc,
            archiver=archiver)

        compiler.shared_lib_extension = so_ext

def get_config_h_filename():
    """Returns the path of pyconfig.h."""
    inc_dir = get_python_inc(plat_specific=1)
    return os.path.join(inc_dir, 'pyconfig.h')

from sysconfig_cpython import (
    parse_makefile, _variable_rx, expand_makefile_vars)

