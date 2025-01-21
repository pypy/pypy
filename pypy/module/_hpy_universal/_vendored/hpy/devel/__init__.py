# NOTE: this file is also imported by PyPy tests, so it must be compatible
# with both Python 2.7 and Python 3.x

import sys
import os.path
import functools
import re
from pathlib import Path

# setuptools >= 60.2 ships its own version of distutils, which monkey-patches
# the stdlib one. Here we ensure that we are using setuptool's.
#
# But this file needs to be importable also in py27 (for pypy tests), and we
# don't care about setuptools version in that case.
import setuptools
import distutils
if (sys.version_info.major > 2 and
    distutils is not getattr(setuptools, '_distutils', None)):
    raise Exception(
        "setuptools' monkey-patching of distutils did not work. "
        "Most likely this is caused by:\n"
        "  - a too old setuptools. Try installing setuptools>=60.2\n"
        "  - the env variable SETUPTOOLS_USE_DISTUTILS=stdlib. Try to unset it."
        )
from distutils import log
from distutils.errors import DistutilsError
import setuptools.command as cmd
try:
    import setuptools.command.build
except ImportError:
    print(
        "warning: setuptools.command.build does not exist in setuptools",
        setuptools.__version__, "on", sys.version
    )
    setuptools.command.build = None
import setuptools.command.build_ext
import setuptools.command.bdist_egg

from .abitag import get_hpy_ext_suffix

DEFAULT_HPY_ABI = 'universal'
if hasattr(sys, 'implementation') and sys.implementation.name == 'cpython':
    DEFAULT_HPY_ABI = 'cpython'


class HPyDevel:
    """ Extra sources for building HPy extensions with hpy.devel. """

    _DEFAULT_BASE_DIR = Path(__file__).parent

    def __init__(self, base_dir=_DEFAULT_BASE_DIR):
        self.base_dir = Path(base_dir)
        self.include_dir = self.base_dir.joinpath('include')
        self.src_dir = self.base_dir.joinpath('src', 'runtime')
        self._available_static_libs = None

    def get_extra_include_dirs(self):
        """ Extra include directories needed by extensions in both CPython and
            Universal modes.
        """
        return list(map(str, [
            self.include_dir,
        ]))

    def get_include_dir_forbid_python_h(self):
        return self.include_dir.joinpath('hpy', 'forbid_python_h')

    def get_extra_sources(self):
        """ Extra sources needed by extensions in both CPython and Universal
            modes.
        """
        return list(map(str, [
            self.src_dir.joinpath('argparse.c'),
            self.src_dir.joinpath('buildvalue.c'),
            self.src_dir.joinpath('format.c'),
            self.src_dir.joinpath('helpers.c'),
            self.src_dir.joinpath('structseq.c'),
        ]))

    def _scan_static_lib_dir(self):
        """ Scan the static library directory and build a dict for all
            available static libraries. The library directory contains
            subdirectories for each ABI and the ABI folders then contain
            the static libraries.
        """
        available_libs = {}
        lib_dir = self.base_dir.joinpath('lib')
        if lib_dir.exists():
            for abi_dir in lib_dir.iterdir():
                if abi_dir.is_dir():
                    abi = abi_dir.name
                    # All files in '.../lib/<abi>/' are considered to be static
                    # libraries.
                    available_libs[abi] = \
                        [str(x) for x in abi_dir.iterdir() if x.is_file()]
        return available_libs

    def get_static_libs(self, hpy_abi):
        """ The list of necessary static libraries an HPy extension needs to
            link to or 'None' (if not available). The HPy ext needs to link to
            all static libraries in the list otherwise some function may stay
            unresolved. For example, there is library 'hpyextra' which contains
            compiled HPy helper functions like 'HPyArg_Parse' and such.
            Libraries are always specific to an ABI.
        """
        if not self._available_static_libs:
            # lazily initialize the dict of available (=shipped) static libs
            self._available_static_libs = self._scan_static_lib_dir()
        return self._available_static_libs.get(hpy_abi, None)

    def get_ctx_sources(self):
        """ Extra sources needed only in the CPython ABI mode.
        """
        return list(map(str, self.src_dir.glob('ctx_*.c')))

    def fix_distribution(self, dist):
        """ Override build_ext to support hpy modules.

            Used from both setup.py and hpy/test.
        """
        # ============= Distribution ==========
        dist.hpydevel = self

        @monkeypatch(dist.__class__)
        def has_ext_modules(self):
            if self.ext_modules or self.hpy_ext_modules:
                return True
            return False

        # ============= build ==========
        if cmd.build is not None:
            build = dist.cmdclass.get("build", cmd.build.build)
            build_hpy = make_mixin(build, build_hpy_mixin)
            dist.cmdclass['build'] = build_hpy

        # ============= build_ext ==========
        build_ext = dist.cmdclass.get("build_ext", cmd.build_ext.build_ext)
        self.build_ext_sanity_check(build_ext)
        build_ext_hpy = make_mixin(build_ext, build_ext_hpy_mixin)
        dist.cmdclass['build_ext'] = build_ext_hpy

        # ============= bdist_egg ==========
        @monkeypatch(setuptools.command.bdist_egg)
        def write_stub(resource, pyfile):
            """
            This is needed because the default bdist_egg unconditionally writes a .py
            stub, thus overwriting the one which was created by
            build_ext_hpy_mixin.write_stub.
            """
            ext_suffix = None
            if dist.hpy_abi != 'cpython':
                ext_suffix = get_hpy_ext_suffix(dist.hpy_abi)
            #
            if ext_suffix and resource.endswith(ext_suffix):
                log.info("stub file already created for %s", resource)
            else:
                write_stub.super(resource, pyfile)

    def build_ext_sanity_check(self, build_ext):
        # check that the supplied build_ext inherits from setuptools
        if isinstance(build_ext, type):
            assert ('setuptools.command.build_ext', 'build_ext') in [
                (c.__module__, c.__name__) for c in build_ext.__mro__
            ], (
                "dist.cmdclass['build_ext'] does not inherit from"
                " setuptools.command.build_ext.build_ext. The HPy build"
                " system does not currently support any other build_ext"
                " classes. If you are using distutils.commands.build_ext,"
                " please use setuptools.commands.build_ext instead."
            )


def handle_hpy_ext_modules(dist, attr, hpy_ext_modules):
    """ Distuils hpy_ext_module setup(...) argument and --hpy-abi option.

        See hpy's setup.py where this function is registered as an entry
        point.
    """
    assert attr == 'hpy_ext_modules'

    # It can happen that this hook will be called multiple times depending on
    # which command was used. So, skip patching if we already patched the
    # distribution.
    if getattr(dist, 'hpydevel', None):
        return

    # add a global option --hpy-abi to setup.py
    dist.__class__.hpy_abi = DEFAULT_HPY_ABI
    dist.__class__.hpy_use_static_libs = False
    dist.__class__.global_options += [
        ('hpy-abi=', None, 'Specify the HPy ABI mode (default: %s)'
                           % DEFAULT_HPY_ABI),
        ('hpy-use-static-libs', None, 'Use static library containing context '
                                      'and helper functions for building '
                                      'extensions (default: False)')
    ]
    hpydevel = HPyDevel()
    hpydevel.fix_distribution(dist)


_HPY_UNIVERSAL_MODULE_STUB_TEMPLATE = """
# DO NOT EDIT THIS FILE!
# This file is automatically generated by hpy

def __bootstrap__():

    from sys import modules
    from os import environ
    from pkg_resources import resource_filename
    from hpy.universal import _load_bootstrap
    ext_filepath = resource_filename(__name__, {ext_file!r})
    m = _load_bootstrap({module_name!r}, __name__, __package__, ext_filepath,
                        __loader__, __spec__, environ)
    modules[__name__] = m

__bootstrap__()
"""


class HPyExtensionName(str):
    """ Wrapper around str to allow HPy extension modules to be identified.

        The following build_ext command methods are passed only the *name*
        of the extension and not the full extension object. The
        build_ext_hpy_mixin class needs to detect when HPy are extensions
        passed to these methods and override the default behaviour.

        This str sub-class allows HPy extensions to be detected, while
        still allowing the extension name to be used as an ordinary string.
    """

    def split(self, *args, **kw):
        result = str.split(self, *args, **kw)
        return [self.__class__(s) for s in result]

    def translate(self, *args, **kw):
        result = str.translate(self, *args, **kw)
        return self.__class__(result)


def is_hpy_extension(ext_name):
    """ Return True if the extension name is for an HPy extension. """
    return isinstance(ext_name, HPyExtensionName)


def remember_hpy_extension(f):
    """ Decorator for remembering whether an extension name belongs to an
        HPy extension.
    """
    @functools.wraps(f)
    def wrapper(self, ext_name):
        if self._only_hpy_extensions:
            assert is_hpy_extension(ext_name), (
                "Extension name %r is not marked as an HPyExtensionName"
                " but only HPy extensions are present. This is almost"
                " certainly a bug in HPy's overriding of setuptools"
                " build_ext. Please report this error the HPy maintainers."
                % (ext_name,)
            )
        result = f(self, ext_name)
        if is_hpy_extension(ext_name):
            result = HPyExtensionName(result)
        return result
    return wrapper


# ==================================================
# Augmented setuptools commands and monkeypatching
# ==================================================

def make_mixin(base, mixin):
    """
    Create a new class which inherits from both mixin and base, so that the
    methods of mixin effectively override the ones of base
    """
    class NewClass(mixin, base, object):
        _mixin_super = base
    NewClass.__name__ = base.__name__ + '_hpy'
    return NewClass

def monkeypatch(target):
    """
    Decorator to monkey patch a function in a module. The original function
    will be available as new_function.super()
    """
    def decorator(fn):
        name = fn.__name__
        fn.super = getattr(target, name)
        setattr(target, name, fn)
        return fn
    return decorator


class build_hpy_mixin:
    """ A mixin class to override setuptools.commands.build """

    def finalize_options(self):
        self._mixin_super.finalize_options(self)
        if self.distribution.hpy_abi != 'cpython':
            suffix = '-hpy-%s' % self.distribution.hpy_abi
            self.build_platlib += suffix
            self.build_lib += suffix
            self.build_temp += suffix


class build_ext_hpy_mixin:
    """ A mixin class to override setuptools.commands.build_ext """

    # Ideally we would have simply added the HPy extensions to .extensions
    # at the end of .initialize_options() but the setuptools build_ext
    # .finalize_options both iterate over and needless overwrite the
    # .extensions attribute, so we hide the full extension list in
    # ._extensions and expose it as a settable property that ignores attempts
    # to overwrite it:

    _extensions = None

    @property
    def extensions(self):
        return self._extensions

    @extensions.setter
    def extensions(self, value):
        pass  # ignore any attempts to change the list of extensions directly

    def initialize_options(self):
        self._mixin_super.initialize_options(self)
        self.hpydevel = self.distribution.hpydevel

    def _finalize_hpy_ext(self, ext):
        if hasattr(ext, "hpy_abi"):
            return
        ext.name = HPyExtensionName(ext.name)
        ext.hpy_abi = self.distribution.hpy_abi
        ext.include_dirs += self.hpydevel.get_extra_include_dirs()
        # If static libs should be used, then add all available libs (for
        # the given ABI) to the extra objects. The libs will then just be added
        # in the linking phase but nothing will be compiled in addition.
        static_libs = self.distribution.hpy_use_static_libs
        if static_libs:
            static_libs = self.hpydevel.get_static_libs(ext.hpy_abi)
            if static_libs is None or len(static_libs) != 1:
                raise DistutilsError('Expected exactly one static library for '
                                     'ABI "%s" but got: %r' %
                                     (ext.hpy_abi, static_libs))

        if static_libs:
            ext.extra_objects += static_libs
        else:
            # If we should not use (pre-compiled) static libs or if they are
            # not available, we just add the sources of the helpers to the
            # extension. They are then compiler with the extension.
            ext.sources += self.hpydevel.get_extra_sources()
        ext.define_macros.append(('HPY', None))
        if ext.hpy_abi == 'cpython':
            # If the user disabled using static libs, we need to add the
            # context sources in this case.
            if not static_libs:
                ext.sources += self.hpydevel.get_ctx_sources()
            ext.define_macros.append(('HPY_ABI_CPYTHON', None))
            ext._hpy_needs_stub = False
        elif ext.hpy_abi == 'hybrid':
            ext.define_macros.append(('HPY_ABI_HYBRID', None))
            ext._hpy_needs_stub = True
        elif ext.hpy_abi == 'universal':
            ext.define_macros.append(('HPY_ABI_UNIVERSAL', None))
            ext._hpy_needs_stub = True
            forbid_python_h = self.hpydevel.get_include_dir_forbid_python_h()
            ext.include_dirs.insert(0, forbid_python_h)
        else:
            raise DistutilsError('Unknown HPy ABI: %s. Valid values are: '
                                 'cpython, hybrid, universal' % ext.hpy_abi)

    def finalize_options(self):
        self._extensions = self.distribution.ext_modules or []
        # _only_hpy_extensions is used only as a sanity check that no
        # hpy extensions are misidentified as legacy C API extensions in the
        # case where only hpy extensions are present.
        self._only_hpy_extensions = not bool(self._extensions)
        hpy_ext_modules = self.distribution.hpy_ext_modules or []
        for ext in hpy_ext_modules:
            self._finalize_hpy_ext(ext)
        self._extensions.extend(hpy_ext_modules)
        self._mixin_super.finalize_options(self)
        for ext in hpy_ext_modules:
            ext._needs_stub = ext._hpy_needs_stub

    @remember_hpy_extension
    def get_ext_fullname(self, ext_name):
        return self._mixin_super.get_ext_fullname(self, ext_name)

    @remember_hpy_extension
    def get_ext_fullpath(self, ext_name):
        return self._mixin_super.get_ext_fullpath(self, ext_name)

    @remember_hpy_extension
    def get_ext_filename(self, ext_name):
        hpy_abi = self.distribution.hpy_abi
        if not is_hpy_extension(ext_name) or hpy_abi == 'cpython':
            return self._mixin_super.get_ext_filename(self, ext_name)
        else:
            assert is_hpy_extension(ext_name)
            assert hpy_abi in ('universal', 'hybrid')
            ext_path = ext_name.split('.')
            ext_suffix = get_hpy_ext_suffix(hpy_abi)
            ext_filename = os.path.join(*ext_path) + ext_suffix
            return ext_filename

    def write_stub(self, output_dir, ext, compile=False):
        if (not hasattr(ext, "hpy_abi") or
                self.distribution.hpy_abi not in ('universal', 'hybrid')):
            return self._mixin_super.write_stub(
                self, output_dir, ext, compile=compile)
        pkgs = ext._full_name.split('.')
        if compile:
            # compile is true when .write_stub is called while copying
            # extensions to the source folder as part of build_ext --inplace.
            # In this situation, output_dir includes the folders that make up
            # the packages containing the module. When compile is false,
            # output_dir does not include those folders (and is just the
            # build_lib folder).
            pkgs = [pkgs[-1]]
        stub_file = os.path.join(output_dir, *pkgs) + '.py'
        log.info(
            "writing hpy universal stub loader for %s to %s",
            ext._full_name, stub_file)

        ext_file = os.path.basename(ext._file_name)
        module_name = ext_file.split(".")[0]
        if not self.dry_run:
            with open(stub_file, 'w', encoding='utf-8') as f:
                f.write(_HPY_UNIVERSAL_MODULE_STUB_TEMPLATE.format(
                    ext_file=ext_file, module_name=module_name)
                )

    def copy_extensions_to_source(self):
        """Override from setuptools 64.0.0 to copy our stub instead of recreating it."""
        build_py = self.get_finalized_command('build_py')
        build_lib = build_py.build_lib
        for ext in self.extensions:
            inplace_file, regular_file = self._get_inplace_equivalent(build_py, ext)

            # Always copy, even if source is older than destination, to ensure
            # that the right extensions for the current Python/platform are
            # used.
            if os.path.exists(regular_file) or not ext.optional:
                self.copy_file(regular_file, inplace_file, level=self.verbose)

            if ext._needs_stub:
                source_stub = os.path.join(build_lib, *ext._full_name.split('.')) + '.py'
                inplace_stub = self._get_equivalent_stub(ext, inplace_file)
                self.copy_file(source_stub, inplace_stub, level=self.verbose)

    def get_export_symbols(self, ext):
        """ Override .get_export_symbols to replace "PyInit_<module_name>"
            with "HPyInit_<module_name>.

            Only relevant on Windows, where the .pyd file (DLL) must export the
            module "HPyInit_" function.
        """
        exports = self._mixin_super.get_export_symbols(self, ext)
        if hasattr(ext, "hpy_abi") and ext.hpy_abi in ('universal', 'hybrid'):
            exports = [re.sub(r"^PyInit_", "HPyInit_", name) for name in exports]
        return exports
