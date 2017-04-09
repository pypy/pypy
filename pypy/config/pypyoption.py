import os
import sys

import py

from rpython.config.config import (OptionDescription, BoolOption, IntOption,
  ChoiceOption, StrOption, to_optparse)
from rpython.config.translationoption import IS_64_BITS


modulepath = py.path.local(__file__).dirpath().dirpath().join("module")
all_modules = [p.basename for p in modulepath.listdir()
               if p.check(dir=True, dotfile=False)
               and p.join('__init__.py').check()
               and not p.basename.startswith('test')]

essential_modules = set([
    "exceptions", "_file", "sys", "__builtin__", "posix", "_warnings",
    "itertools"
])

default_modules = essential_modules.copy()
default_modules.update([
    "_codecs", "gc", "_weakref", "marshal", "errno", "imp", "math", "cmath",
    "_sre", "_pickle_support", "operator", "parser", "symbol", "token", "_ast",
    "_io", "_random", "__pypy__", "_testing", "time"
])


# --allworkingmodules
working_modules = default_modules.copy()
working_modules.update([
    "_socket", "unicodedata", "mmap", "fcntl", "_locale", "pwd",
    "select", "zipimport", "_lsprof", "crypt", "signal", "_rawffi", "termios",
    "zlib", "bz2", "struct", "_hashlib", "_md5", "_sha", "_minimal_curses",
    "cStringIO", "thread", "itertools", "pyexpat", "_ssl", "cpyext", "array",
    "binascii", "_multiprocessing", '_warnings', "_collections",
    "_multibytecodec", "micronumpy", "_continuation", "_cffi_backend",
    "_csv", "cppyy", "_pypyjson", "_jitlog"
])

from rpython.jit.backend import detect_cpu
try:
    if detect_cpu.autodetect().startswith('x86'):
        working_modules.add('_vmprof')
        working_modules.add('faulthandler')
except detect_cpu.ProcessorAutodetectError:
    pass

translation_modules = default_modules.copy()
translation_modules.update([
    "fcntl", "time", "select", "signal", "_rawffi", "zlib", "struct", "_md5",
    "cStringIO", "array", "binascii",
    # the following are needed for pyrepl (and hence for the
    # interactive prompt/pdb)
    "termios", "_minimal_curses",
])

# XXX this should move somewhere else, maybe to platform ("is this posixish"
#     check or something)
if sys.platform == "win32":
    working_modules.add("_winreg")
    # unix only modules
    for name in ["crypt", "fcntl", "pwd", "termios", "_minimal_curses"]:
        working_modules.remove(name)
        if name in translation_modules:
            translation_modules.remove(name)

    if "cppyy" in working_modules:
        working_modules.remove("cppyy")  # not tested on win32
    if "faulthandler" in working_modules:
        working_modules.remove("faulthandler")  # missing details

    # The _locale module is needed by site.py on Windows
    default_modules.add("_locale")

if sys.platform == "sunos5":
    working_modules.remove('fcntl')  # LOCK_NB not defined
    working_modules.remove("_minimal_curses")
    working_modules.remove("termios")
    if "cppyy" in working_modules:
        working_modules.remove("cppyy")  # depends on ctypes

#if sys.platform.startswith("linux"):
#    _mach = os.popen('uname -m', 'r').read().strip()
#    if _mach.startswith(...):
#        working_modules.remove("_continuation")


module_dependencies = {
    '_multiprocessing': [('objspace.usemodules.time', True),
                         ('objspace.usemodules.thread', True)],
    'cpyext': [('objspace.usemodules.array', True)],
    'cppyy': [('objspace.usemodules.cpyext', True)],
    'faulthandler': [('objspace.usemodules._vmprof', True)],
    }
module_suggests = {
    # the reason you want _rawffi is for ctypes, which
    # itself needs the interp-level struct module
    # because 'P' is missing from the app-level one
    "_rawffi": [("objspace.usemodules.struct", True)],
    "cpyext": [("translation.secondaryentrypoints", "cpyext,main")],
}
if sys.platform == "win32":
    module_suggests["cpyext"].append(("translation.shared", True))


# NOTE: this dictionary is not used any more
module_import_dependencies = {
    # no _rawffi if importing rpython.rlib.clibffi raises ImportError
    # or CompilationError or py.test.skip.Exception
    "_rawffi"   : ["rpython.rlib.clibffi"],

    "zlib"      : ["rpython.rlib.rzlib"],
    "bz2"       : ["pypy.module.bz2.interp_bz2"],
    "pyexpat"   : ["pypy.module.pyexpat.interp_pyexpat"],
    "_ssl"      : ["pypy.module._ssl.interp_ssl"],
    "_hashlib"  : ["pypy.module._ssl.interp_ssl"],
    "_minimal_curses": ["pypy.module._minimal_curses.fficurses"],
    "_continuation": ["rpython.rlib.rstacklet"],
    "_vmprof"      : ["pypy.module._vmprof.interp_vmprof"],
    "faulthandler" : ["pypy.module._vmprof.interp_vmprof"],
    }

def get_module_validator(modname):
    # NOTE: this function is not used any more
    if modname in module_import_dependencies:
        modlist = module_import_dependencies[modname]
        def validator(config):
            from rpython.rtyper.tool.rffi_platform import CompilationError
            try:
                for name in modlist:
                    __import__(name)
            except (ImportError, CompilationError, py.test.skip.Exception) as e:
                errcls = e.__class__.__name__
                raise Exception(
                    "The module %r is disabled\n" % (modname,) +
                    "because importing %s raised %s\n" % (name, errcls) +
                    str(e))
        return validator
    else:
        return None


pypy_optiondescription = OptionDescription("objspace", "Object Space Options", [
    OptionDescription("usemodules", "Which Modules should be used", [
        BoolOption(modname, "use module %s" % (modname, ),
                   default=modname in default_modules,
                   cmdline="--withmod-%s" % (modname, ),
                   requires=module_dependencies.get(modname, []),
                   suggests=module_suggests.get(modname, []),
                   negation=modname not in essential_modules,
                   ) #validator=get_module_validator(modname))
        for modname in all_modules]),

    BoolOption("allworkingmodules", "use as many working modules as possible",
               # NB. defaults to True, but in py.py this is overridden by
               # a False suggestion because it takes a while to start up.
               # Actual module enabling only occurs if
               # enable_allworkingmodules() is called, and it depends
               # on the selected backend.
               default=True,
               cmdline="--allworkingmodules",
               negation=True),

    StrOption("extmodules",
              "Comma-separated list of third-party builtin modules",
              cmdline="--ext",
              default=None),

    BoolOption("translationmodules",
          "use only those modules that are needed to run translate.py on pypy",
               default=False,
               cmdline="--translationmodules",
               suggests=[("objspace.allworkingmodules", False)]),

    BoolOption("lonepycfiles", "Import pyc files with no matching py file",
               default=False),

    StrOption("soabi",
              "Tag to differentiate extension modules built for different Python interpreters",
              cmdline="--soabi",
              default=None),

    BoolOption("honor__builtins__",
               "Honor the __builtins__ key of a module dictionary",
               default=False),

    BoolOption("disable_call_speedhacks",
               "make sure that all calls go through space.call_args",
               default=False),

    BoolOption("disable_entrypoints",
               "Disable external entry points, notably the"
               " cpyext module and cffi's embedding mode.",
               default=False,
               requires=[("objspace.usemodules.cpyext", False)]),

    ChoiceOption("hash",
                 "The hash function to use for strings: fnv from CPython 2.7"
                 " or siphash24 from CPython >= 3.4",
                 ["fnv", "siphash24"],
                 default="fnv",
                 cmdline="--hash"),

    OptionDescription("std", "Standard Object Space Options", [
        BoolOption("withtproxy", "support transparent proxies",
                   default=True),

        BoolOption("withprebuiltint", "prebuild commonly used int objects",
                   default=False),

        IntOption("prebuiltintfrom", "lowest integer which is prebuilt",
                  default=-5, cmdline="--prebuiltintfrom"),

        IntOption("prebuiltintto", "highest integer which is prebuilt",
                  default=100, cmdline="--prebuiltintto"),

        BoolOption("withsmalllong", "use a version of 'long' in a C long long",
                   default=False),

        BoolOption("withstrbuf", "use strings optimized for addition (ver 2)",
                   default=False),

        BoolOption("withspecialisedtuple",
                   "use specialised tuples",
                   default=False),

        BoolOption("withcelldict",
                   "use dictionaries that are optimized for being used as module dicts",
                   default=False,
                   requires=[("objspace.honor__builtins__", False)]),

        BoolOption("withliststrategies",
                   "enable optimized ways to store lists of primitives ",
                   default=True),

        BoolOption("withmethodcachecounter",
                   "try to cache methods and provide a counter in __pypy__. "
                   "for testing purposes only.",
                   default=False),
        IntOption("methodcachesizeexp",
                  " 2 ** methodcachesizeexp is the size of the of the method cache ",
                  default=11),
        BoolOption("intshortcut",
                   "special case addition and subtraction of two integers in BINARY_ADD/"
                   "/BINARY_SUBTRACT and their inplace counterparts",
                   default=False),
        BoolOption("optimized_list_getitem",
                   "special case the 'list[integer]' expressions",
                   default=False),
        BoolOption("newshortcut",
                   "cache and shortcut calling __new__ from builtin types",
                   default=False),

     ]),
])

def get_pypy_config(overrides=None, translating=False):
    from rpython.config.translationoption import get_combined_translation_config
    return get_combined_translation_config(
            pypy_optiondescription, overrides=overrides,
            translating=translating)

def set_pypy_opt_level(config, level):
    """Apply PyPy-specific optimization suggestions on the 'config'.
    The optimizations depend on the selected level and possibly on the backend.
    """
    # all the good optimizations for PyPy should be listed here
    if level in ['2', '3', 'jit']:
        config.objspace.std.suggest(intshortcut=True)
        config.objspace.std.suggest(optimized_list_getitem=True)
        #config.objspace.std.suggest(newshortcut=True)
        config.objspace.std.suggest(withspecialisedtuple=True)
        #if not IS_64_BITS:
        #    config.objspace.std.suggest(withsmalllong=True)

    # extra costly optimizations only go in level 3
    if level == '3':
        config.translation.suggest(profopt=
            "-c 'from richards import main;main(); "
                "from test import pystone; pystone.main()'")

    # memory-saving optimizations
    if level == 'mem':
        config.objspace.std.suggest(withprebuiltint=True)
        config.objspace.std.suggest(withliststrategies=True)
        if not IS_64_BITS:
            config.objspace.std.suggest(withsmalllong=True)

    # extra optimizations with the JIT
    if level == 'jit':
        config.objspace.std.suggest(withcelldict=True)


def enable_allworkingmodules(config):
    modules = working_modules.copy()
    if config.translation.sandbox:
        modules = default_modules
    # ignore names from 'essential_modules', notably 'exceptions', which
    # may not be present in config.objspace.usemodules at all
    modules = [name for name in modules if name not in essential_modules]

    # the llvm translation backend currently doesn't support cpyext
    # cppyy depends in cpyext
    if config.translation.backend == 'llvm':
        modules.remove('cpyext')
        modules.remove('cppyy')

    config.objspace.usemodules.suggest(**dict.fromkeys(modules, True))

def enable_translationmodules(config):
    modules = translation_modules
    modules = [name for name in modules if name not in essential_modules]
    config.objspace.usemodules.suggest(**dict.fromkeys(modules, True))


if __name__ == '__main__':
    config = get_pypy_config()
    print config.getpaths()
    parser = to_optparse(config) #, useoptions=["translation.*"])
    option, args = parser.parse_args()
    print config
