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
    "select", "zipimport", "_lsprof", "signal", "_rawffi", "termios",
    "zlib", "bz2", "struct", "_md5", "_sha", "_minimal_curses",
    "cStringIO", "thread", "itertools", "pyexpat", "cpyext", "array",
    "binascii", "_multiprocessing", '_warnings', "_collections",
    "_multibytecodec", "micronumpy", "_continuation", "_cffi_backend",
    "_csv", "_cppyy", "_pypyjson", "_jitlog",
    # "_hashlib", "crypt"
])

import rpython.rlib.rvmprof.cintf
if rpython.rlib.rvmprof.cintf.IS_SUPPORTED:
    working_modules.add('_vmprof')
    working_modules.add('faulthandler')

translation_modules = default_modules.copy()
translation_modules.update([
    "fcntl", "time", "select", "signal", "_rawffi", "zlib", "struct", "_md5",
    "cStringIO", "array", "binascii",
    # the following are needed for pyrepl (and hence for the
    # interactive prompt/pdb)
    "termios", "_minimal_curses",
])

reverse_debugger_disable_modules = set([
    "_continuation", "_vmprof", "_multiprocessing",
    "micronumpy",
    ])

# XXX this should move somewhere else, maybe to platform ("is this posixish"
#     check or something)
if sys.platform == "win32":
    working_modules.add("_winreg")
    # unix only modules
    for name in ["crypt", "fcntl", "pwd", "termios", "_minimal_curses"]:
        if name in working_modules:
            working_modules.remove(name)
        if name in translation_modules:
            translation_modules.remove(name)

    if "faulthandler" in working_modules:
        working_modules.remove("faulthandler")  # missing details
    if "_vmprof" in working_modules:
        working_modules.remove("_vmprof")  # FIXME: missing details

    # The _locale module is needed by site.py on Windows
    default_modules.add("_locale")

    # needed to invoke MSVC
    translation_modules.update(["thread", "_winreg", "_cffi_backend"])

    # not ported yet
    if IS_64_BITS:
        for name in ["cpyext", "_cppyy", "micronumpy"]:
            if name in working_modules:
                working_modules.remove(name)

if sys.platform == "sunos5":
    working_modules.remove('fcntl')  # LOCK_NB not defined
    working_modules.remove("_minimal_curses")
    working_modules.remove("termios")
    if "_cppyy" in working_modules:
        working_modules.remove("_cppyy")  # depends on ctypes

#if sys.platform.startswith("linux"):
#    _mach = os.popen('uname -m', 'r').read().strip()
#    if _mach.startswith(...):
#        working_modules.remove("_continuation")


module_dependencies = {
    '_multiprocessing': [('objspace.usemodules.time', True),
                         ('objspace.usemodules.thread', True)],
    'cpyext': [('objspace.usemodules.array', True)],
    '_cppyy': [('objspace.usemodules.cpyext', True)],
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


pypy_optiondescription = OptionDescription("objspace", "Object Space Options", [
    OptionDescription("usemodules", "Which Modules should be used", [
        BoolOption(modname, "use module %s" % (modname, ),
                   default=modname in default_modules,
                   cmdline="--withmod-%s" % (modname, ),
                   requires=module_dependencies.get(modname, []),
                   suggests=module_suggests.get(modname, []),
                   negation=modname not in essential_modules,
                   )
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

        BoolOption("withspecialisedtuple",
                   "use specialised tuples",
                   default=False),

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
        BoolOption("reinterpretasserts",
                   "Perform reinterpretation when an assert fails "
                   "(only relevant for tests)",
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
        pass # none at the moment


def enable_allworkingmodules(config):
    modules = working_modules.copy()
    if config.translation.sandbox:
        modules = default_modules
    if config.translation.reverse_debugger:
        for mod in reverse_debugger_disable_modules:
            setattr(config.objspace.usemodules, mod, False)
    # ignore names from 'essential_modules', notably 'exceptions', which
    # may not be present in config.objspace.usemodules at all
    modules = [name for name in modules if name not in essential_modules]

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
    print working_modules
