import sys

import py

from rpython.config.config import (OptionDescription, BoolOption, IntOption,
  ChoiceOption, StrOption, to_optparse, ConflictConfigError)
from rpython.config.translationoption import IS_64_BITS


modulepath = py.path.local(__file__).dirpath().dirpath().join("module")
all_modules = [p.basename for p in modulepath.listdir()
               if p.check(dir=True, dotfile=False)
               and p.join('__init__.py').check()
               and not p.basename.startswith('test')]

essential_modules = dict.fromkeys(
    ["exceptions", "_file", "sys", "__builtin__", "posix", "_warnings"]
)

default_modules = essential_modules.copy()
default_modules.update(dict.fromkeys(
    ["_codecs", "gc", "_weakref", "marshal", "errno", "imp",
     "math", "cmath", "_sre", "_pickle_support", "operator",
     "parser", "symbol", "token", "_ast",  "_io", "_random", "__pypy__",
     "_testing"]))


# --allworkingmodules
working_modules = default_modules.copy()
working_modules.update(dict.fromkeys(
    ["_socket", "unicodedata", "mmap", "fcntl", "_locale", "pwd",
     "rctime" , "select", "zipimport", "_lsprof",
     "crypt", "signal", "_rawffi", "termios", "zlib", "bz2",
     "struct", "_hashlib", "_md5", "_sha", "_minimal_curses", "cStringIO",
     "thread", "itertools", "pyexpat", "_ssl", "cpyext", "array",
     "binascii", "_multiprocessing", '_warnings',
     "_collections", "_multibytecodec", "micronumpy",
     "_continuation", "_cffi_backend", "_csv", "cppyy", "_pypyjson"]
))

translation_modules = default_modules.copy()
translation_modules.update(dict.fromkeys(
    ["fcntl", "rctime", "select", "signal", "_rawffi", "zlib",
     "struct", "_md5", "cStringIO", "array",
     "binascii",
     # the following are needed for pyrepl (and hence for the
     # interactive prompt/pdb)
     "termios", "_minimal_curses",
     ]))

# XXX this should move somewhere else, maybe to platform ("is this posixish"
#     check or something)
if sys.platform == "win32":
    working_modules["_winreg"] = None
    # unix only modules
    del working_modules["crypt"]
    del working_modules["fcntl"]
    del working_modules["pwd"]
    del working_modules["termios"]
    del working_modules["_minimal_curses"]

    if "cppyy" in working_modules:
        del working_modules["cppyy"]  # not tested on win32

    # The _locale module is needed by site.py on Windows
    default_modules["_locale"] = None

if sys.platform == "sunos5":
    del working_modules['mmap']   # depend on ctypes, can't get at c-level 'errono'
    del working_modules['rctime'] # depend on ctypes, missing tm_zone/tm_gmtoff
    del working_modules['signal'] # depend on ctypes, can't get at c-level 'errono'
    del working_modules['fcntl']  # LOCK_NB not defined
    del working_modules["_minimal_curses"]
    del working_modules["termios"]
    del working_modules["_multiprocessing"]   # depends on rctime
    if "cppyy" in working_modules:
        del working_modules["cppyy"]  # depends on ctypes


module_dependencies = {
    '_multiprocessing': [('objspace.usemodules.rctime', True),
                         ('objspace.usemodules.thread', True)],
    'cpyext': [('objspace.usemodules.array', True)],
    'cppyy': [('objspace.usemodules.cpyext', True)],
    }
module_suggests = {
    # the reason you want _rawffi is for ctypes, which
    # itself needs the interp-level struct module
    # because 'P' is missing from the app-level one
    "_rawffi": [("objspace.usemodules.struct", True)],
    "cpyext": [("translation.secondaryentrypoints", "cpyext,main"),
               ("translation.shared", sys.platform == "win32")],
}

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
    }

def get_module_validator(modname):
    if modname in module_import_dependencies:
        modlist = module_import_dependencies[modname]
        def validator(config):
            from rpython.rtyper.tool.rffi_platform import CompilationError
            try:
                for name in modlist:
                    __import__(name)
            except (ImportError, CompilationError, py.test.skip.Exception), e:
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

    BoolOption("usepycfiles", "Write and read pyc files when importing",
               default=True),

    BoolOption("lonepycfiles", "Import pyc files with no matching py file",
               default=False,
               requires=[("objspace.usepycfiles", True)]),

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

        BoolOption("withprebuiltchar",
                   "use prebuilt single-character string objects",
                   default=False),

        BoolOption("sharesmallstr",
                   "always reuse the prebuilt string objects "
                   "(the empty string and potentially single-char strings)",
                   default=False),

        BoolOption("withspecialisedtuple",
                   "use specialised tuples",
                   default=False),

        BoolOption("withcelldict",
                   "use dictionaries that are optimized for being used as module dicts",
                   default=False,
                   requires=[("objspace.honor__builtins__", False)]),

        BoolOption("withmapdict",
                   "make instances really small but slow without the JIT",
                   default=False,
                   requires=[("objspace.std.getattributeshortcut", True),
                             ("objspace.std.withmethodcache", True),
                       ]),

        BoolOption("withrangelist",
                   "enable special range list implementation that does not "
                   "actually create the full list until the resulting "
                   "list is mutated",
                   default=False),
        BoolOption("withliststrategies",
                   "enable optimized ways to store lists of primitives ",
                   default=True),

        BoolOption("withtypeversion",
                   "version type objects when changing them",
                   cmdline=None,
                   default=False,
                   # weakrefs needed, because of get_subclasses()
                   requires=[("translation.rweakref", True)]),

        BoolOption("withmethodcache",
                   "try to cache method lookups",
                   default=False,
                   requires=[("objspace.std.withtypeversion", True),
                             ("translation.rweakref", True)]),
        BoolOption("withmethodcachecounter",
                   "try to cache methods and provide a counter in __pypy__. "
                   "for testing purposes only.",
                   default=False,
                   requires=[("objspace.std.withmethodcache", True)]),
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
        BoolOption("builtinshortcut",
                   "a shortcut for operations between built-in types. XXX: "
                   "deprecated, not really a shortcut any more.",
                   default=False),
        BoolOption("getattributeshortcut",
                   "track types that override __getattribute__",
                   default=False,
                   # weakrefs needed, because of get_subclasses()
                   requires=[("translation.rweakref", True)]),
        BoolOption("newshortcut",
                   "cache and shortcut calling __new__ from builtin types",
                   default=False,
                   # weakrefs needed, because of get_subclasses()
                   requires=[("translation.rweakref", True)]),

        ChoiceOption("multimethods", "the multimethod implementation to use",
                     ["doubledispatch", "mrd"],
                     default="mrd"),
        BoolOption("withidentitydict",
                   "track types that override __hash__, __eq__ or __cmp__ and use a special dict strategy for those which do not",
                   default=False,
                   # weakrefs needed, because of get_subclasses()
                   requires=[("translation.rweakref", True)]),
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
    # warning: during some tests, the type_system and the backend may be
    # unspecified and we get None.  It shouldn't occur in translate.py though.
    type_system = config.translation.type_system
    backend = config.translation.backend

    # all the good optimizations for PyPy should be listed here
    if level in ['2', '3', 'jit']:
        config.objspace.std.suggest(withrangelist=True)
        config.objspace.std.suggest(withmethodcache=True)
        config.objspace.std.suggest(withprebuiltchar=True)
        config.objspace.std.suggest(intshortcut=True)
        config.objspace.std.suggest(optimized_list_getitem=True)
        config.objspace.std.suggest(getattributeshortcut=True)
        #config.objspace.std.suggest(newshortcut=True)
        config.objspace.std.suggest(withspecialisedtuple=True)
        config.objspace.std.suggest(withidentitydict=True)
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
        config.objspace.std.suggest(withrangelist=True)
        config.objspace.std.suggest(withprebuiltchar=True)
        config.objspace.std.suggest(withmapdict=True)
        if not IS_64_BITS:
            config.objspace.std.suggest(withsmalllong=True)

    # extra optimizations with the JIT
    if level == 'jit':
        config.objspace.std.suggest(withcelldict=True)
        config.objspace.std.suggest(withmapdict=True)


def enable_allworkingmodules(config):
    modules = working_modules
    if config.translation.sandbox:
        modules = default_modules
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
