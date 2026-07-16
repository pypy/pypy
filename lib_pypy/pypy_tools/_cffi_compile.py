"""A small, distutils-free compiler driver for building cffi extension modules.

On Python >= 3.12 the stdlib ``distutils`` is gone and cffi normally requires
``setuptools`` to compile out-of-line modules (see
``cffi/_shimmed_dist_utils.py``).  During PyPy's own build that creates a
chicken-and-egg problem: ``build_cffi_imports`` needs to build ``_ssl`` (used by
hashlib/ssl) *before* ``ensurepip`` can install ``setuptools``, but ``ensurepip``
itself needs ``_ssl``.

This module breaks the cycle by invoking the C compiler and linker directly,
the same way distutils' ``UnixCCompiler``/``MSVCCompiler`` do, but with no
distutils/setuptools dependency.  The toolchain is discovered in this order:

1. the ``PYPY_CC`` / ``PYPY_CC_LINK`` / ``PYPY_CC_KIND`` environment variables,
   which PyPy's translation driver sets from ``rpython.translator.platform``
   (this is how the Windows MSVC environment is handed down -- the host already
   located ``cl.exe``/``link.exe`` and their ``INCLUDE``/``LIB`` env);
2. ``sysconfig`` config vars (``CC``, ``LDSHARED``, ...), which a normal
   installed PyPy populates from ``_sysconfigdata`` -- this keeps the
   user-facing ``pypy build_cffi_imports.py`` rebuild working standalone on
   POSIX;
3. nothing else -- if neither is available a clear error is raised.
"""
import os
import shlex
import subprocess
import sys
import sysconfig


class Extension(object):
    """A drop-in stand-in for ``distutils.core.Extension``.

    Only the attributes cffi actually passes through ``get_extension`` are
    honoured; any other distutils keyword (``depends``, ...) is accepted and
    ignored so existing build scripts keep working.
    """
    def __init__(self, name, sources, include_dirs=None, define_macros=None,
                 undef_macros=None, library_dirs=None, libraries=None,
                 extra_compile_args=None, extra_link_args=None,
                 extra_objects=None, **ignored):
        self.name = name
        self.sources = list(sources)
        self.include_dirs = list(include_dirs or [])
        self.define_macros = list(define_macros or [])
        self.undef_macros = list(undef_macros or [])
        self.library_dirs = list(library_dirs or [])
        self.libraries = list(libraries or [])
        self.extra_compile_args = list(extra_compile_args or [])
        self.extra_link_args = list(extra_link_args or [])
        self.extra_objects = list(extra_objects or [])


def _split(cmd):
    if not cmd:
        return []
    if isinstance(cmd, (list, tuple)):
        return list(cmd)
    return shlex.split(cmd, posix=(os.name != 'nt'))


def _kind():
    kind = os.environ.get('PYPY_CC_KIND')
    if kind:
        return kind
    return 'msvc' if sys.platform == 'win32' else 'unix'


def _cc():
    return _split(os.environ.get('PYPY_CC') or
                  sysconfig.get_config_var('CC'))


def _linker(default_cc):
    link = _split(os.environ.get('PYPY_CC_LINK') or
                  sysconfig.get_config_var('LDSHARED'))
    if not link:
        link = list(default_cc)
    return link


def _ext_suffix():
    return (sysconfig.get_config_var('EXT_SUFFIX') or
            sysconfig.get_config_var('SO') or
            ('.pyd' if sys.platform == 'win32' else '.so'))


def _output_filename(modname):
    # mirror distutils.command.build_ext.get_ext_filename: a dotted name maps
    # to a path, with the platform extension suffix appended.
    parts = modname.split('.')
    return os.path.join(*parts) + _ext_suffix()


def _ensure_parent(path):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)


def _run(args, verbose):
    if verbose:
        print(' '.join(args))
    proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    out, _ = proc.communicate()
    if proc.returncode != 0:
        from cffi.error import VerificationError
        if not isinstance(out, str):
            out = out.decode('utf-8', 'replace')
        raise VerificationError(
            '%s\ncommand failed (status %d): %s' %
            (out, proc.returncode, ' '.join(args)))


def _macros(define_macros, undef_macros, prefix):
    args = []
    for name, value in define_macros:
        if value is None:
            args.append('%s%s' % (prefix, name))
        else:
            args.append('%s%s=%s' % (prefix, name, value))
    for name in undef_macros:
        args.append('-U' + name)
    return args


def _build_unix(ext, verbose):
    cc = _cc() or ['cc']
    link = _linker(cc)
    # make sure we actually produce a shared object
    if not (set(link) & set(['-shared', '-bundle', '-dynamiclib'])):
        link = link + ['-shared']

    # honour the standard compiler env vars the way distutils' UnixCCompiler
    # does -- create_cffi_import_libraries injects the PyPy INCLUDEPY into
    # CFLAGS and (for --embed-dependencies) the bundled openssl dirs into
    # CPPFLAGS/LDFLAGS.
    cflags = _split(os.environ.get('CFLAGS') or
                    sysconfig.get_config_var('CFLAGS'))
    cppflags = _split(os.environ.get('CPPFLAGS'))
    ldflags = _split(os.environ.get('LDFLAGS'))
    ccshared = _split(sysconfig.get_config_var('CCSHARED'))
    if not ccshared:
        ccshared = ['-fPIC']
    includepy = sysconfig.get_config_var('INCLUDEPY')

    objects = []
    for src in ext.sources:
        obj = os.path.splitext(os.path.basename(src))[0] + '.o'
        args = list(cc) + cflags + cppflags + ccshared
        if includepy:
            args.append('-I' + includepy)
        args += ['-I' + d for d in ext.include_dirs]
        args += _macros(ext.define_macros, ext.undef_macros, '-D')
        args += ext.extra_compile_args
        args += ['-c', src, '-o', obj]
        _run(args, verbose)
        objects.append(obj)

    out = _output_filename(ext.name)
    _ensure_parent(out)
    args = list(link) + ldflags + objects + ext.extra_objects
    args += ['-L' + d for d in ext.library_dirs]
    args += ['-l' + l for l in ext.libraries]
    args += ext.extra_link_args
    args += ['-o', out]
    _run(args, verbose)
    return out


def _build_msvc(ext, verbose):
    # NB: validated on POSIX; the MSVC command lines mirror distutils'
    # MSVCCompiler and rely on the translation driver having exported the
    # vcvars environment (INCLUDE/LIB/PATH) so cl.exe/link.exe are usable.
    cc = _cc() or ['cl.exe']
    link = _split(os.environ.get('PYPY_CC_LINK')) or ['link.exe']
    includepy = sysconfig.get_config_var('INCLUDEPY')

    objects = []
    for src in ext.sources:
        obj = os.path.splitext(os.path.basename(src))[0] + '.obj'
        args = list(cc) + ['/nologo', '/O2', '/MD', '/c']
        if includepy:
            args.append('/I' + includepy)
        args += ['/I' + d for d in ext.include_dirs]
        args += _macros(ext.define_macros, ext.undef_macros, '/D')
        args += ext.extra_compile_args
        args += [src, '/Fo' + obj]
        _run(args, verbose)
        objects.append(obj)

    out = _output_filename(ext.name)
    _ensure_parent(out)
    # the C extension must export its module init function
    init = 'PyInit_' + ext.name.split('.')[-1]
    args = list(link) + ['/nologo', '/DLL', '/EXPORT:' + init]
    args += ['/OUT:' + out] + objects + ext.extra_objects
    args += ['/LIBPATH:' + d for d in ext.library_dirs]
    args += [l if l.lower().endswith('.lib') else l + '.lib'
             for l in ext.libraries]
    args += ext.extra_link_args
    _run(args, verbose)
    return out


def build(ext, tmpdir='.', compiler_verbose=0, debug=None):
    """Compile and link ``ext`` (an :class:`Extension`) in ``tmpdir``.

    Returns the path to the produced shared object (relative to ``tmpdir``,
    which the caller has already ``chdir``-ed into, matching
    ``cffi.ffiplatform``).
    """
    if _kind() == 'msvc':
        return _build_msvc(ext, compiler_verbose)
    return _build_unix(ext, compiler_verbose)


def compile_shared(csource, modulename, output_dir, include_dirs=None,
                   define_macros=None, libraries=None, library_dirs=None,
                   extra_compile_args=None, extra_link_args=None,
                   compiler_verbose=0):
    """Compile one or more C sources into an extension module, distutils-free.

    A sibling of :func:`cffi.ffiplatform.compile`: both sit on
    :class:`Extension`/:func:`build`, but this one packages the build the
    on-demand C test modules (``_testcapi``, ``_ctypes_test``, ...) used to do
    through ``distutils.ccompiler``.  ``csource`` is a single source path or a
    list of them; they are compiled and linked into ``modulename`` inside
    ``output_dir`` and the absolute path of the produced shared object is
    returned.  The PyPy header dir (INCLUDEPY) and, on MSVC, the ``PyInit_``
    export are added by :func:`build` itself.
    """
    if isinstance(csource, str):
        sources = [csource]
    else:
        sources = list(csource)
    ext = Extension(modulename, sources, include_dirs=include_dirs,
                    define_macros=define_macros, libraries=libraries,
                    library_dirs=library_dirs,
                    extra_compile_args=extra_compile_args,
                    extra_link_args=extra_link_args)
    oldcwd = os.getcwd()
    os.chdir(output_dir)
    try:
        out = build(ext, output_dir, compiler_verbose)
    finally:
        os.chdir(oldcwd)
    return os.path.join(output_dir, out)
