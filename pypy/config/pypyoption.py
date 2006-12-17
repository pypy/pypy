import autopath
import py, os
from pypy.config.config import OptionDescription, BoolOption, IntOption, ArbitraryOption
from pypy.config.config import ChoiceOption, StrOption, to_optparse, Config

modulepath = py.magic.autopath().dirpath().dirpath().join("module")
all_modules = [p.basename for p in modulepath.listdir()
                   if p.check(dir=True, dotfile=False)]

default_modules = dict.fromkeys(
    [#"unicodedata",
     "_codecs", "gc", "_weakref", "array", "marshal", "errno",
     "math", "_sre", "_pickle_support", "sys", "exceptions", "__builtins__",
     "recparser", "symbol", "_random", "_file", "pypymagic"])

module_dependencies = { }
if os.name == "posix":
    module_dependencies['rctime'] = [("objspace.usemodules.select", True),]

                              
pypy_optiondescription = OptionDescription("objspace", "Object Space Option", [
    ChoiceOption("name", "Object Space name",
                 ["std", "flow", "logic", "thunk", "cpy", "dump", "taint"],
                 "std",
                 requires = {
                     "thunk": [("objspace.geninterp", False)],
                     "logic": [("objspace.geninterp", False),
                               ("objspace.usemodules._stackless", True)],
                 },
                 cmdline='--objspace -o'),

    ChoiceOption("parser", "parser",
                 ["pypy", "cpython"], "pypy",
                 cmdline='--parser'),

    ChoiceOption("compiler", "compiler",
                 ["cpython", "ast"], "ast",
                 cmdline='--compiler'),

    OptionDescription("opcodes", "opcodes to enable in the interpreter", [
        ]),

    BoolOption("nofaking", "disallow faking in the object space",
               default=False,
               requires=[
                   ("objspace.usemodules.posix", True),
                   ("objspace.usemodules.time", True),
                   ("objspace.usemodules.errno", True)],
               cmdline='--nofaking'),

    OptionDescription("usemodules", "Which Modules should be used", [
        BoolOption(modname, "use module %s" % (modname, ),
                   default=modname in default_modules,
                   cmdline="--withmod-%s" % (modname, ),
                   requires= module_dependencies.get(modname, []))
        for modname in all_modules]),

    BoolOption("geninterp", "specify whether geninterp should be used",
               default=True),

    BoolOption("logbytecodes",
               "keep track of bytecode usage",
               default=False),

    BoolOption("usepycfiles", "Write and read pyc files when importing",
               default=True),
   
    OptionDescription("std", "Standard Object Space Options", [
        BoolOption("withtproxy", "support transparent proxies",
                   default=False, cmdline='--with-transparent-proxy'),

        BoolOption("withsmallint", "use tagged integers",
                   default=False),

        BoolOption("withprebuiltint", "prebuilt commonly used int objects",
                   default=False,
                   requires=[("objspace.std.withsmallint", False)]),

        IntOption("prebuiltintfrom", "lowest integer which is prebuilt",
                  default=-5, cmdline="--prebuiltinfrom"),

        IntOption("prebuiltintto", "highest integer which is prebuilt",
                  default=100, cmdline="--prebuiltintto"),

        BoolOption("withstrjoin", "use strings optimized for addition",
                   default=False),

        BoolOption("withstrslice", "use strings optimized for slicing",
                   default=False),

        BoolOption("withstrdict",
                   "use dictionaries optimized for string keys",
                   default=False),

        BoolOption("withmultidict",
                   "use dictionaries optimized for flexibility",
                   default=False,
                   requires=[("objspace.std.withstrdict", False)]),

        BoolOption("withsharingdict",
                   "use dictionaries that share the keys part",
                   default=False,
                   requires=[("objspace.std.withmultidict", True)]),

        BoolOption("withdictmeasurement",
                   "create huge files with masses of information "
                   "about dictionaries",
                   default=False,
                   requires=[("objspace.std.withmultidict", True)]),

        BoolOption("withrangelist",
                   "enable special range list implementation that does not "
                   "actually create the full list until the resulting "
                   "list is mutaged",
                   default=False),

        BoolOption("oldstyle",
                   "specify whether the default metaclass should be classobj",
                   default=False, cmdline="--oldstyle"),
     ]),
    BoolOption("lowmem", "Try to use little memory during translation",
               default=False, cmdline="--lowmem",
               requires=[("objspace.geninterp", False)]),


])

def get_pypy_config(overrides=None, translating=False):
    from pypy.config.translationoption import get_combined_translation_config
    return get_combined_translation_config(
            pypy_optiondescription, overrides=overrides,
            translating=translating)

if __name__ == '__main__':
    config = get_pypy_config()
    print config.getpaths()
    parser = to_optparse(config) #, useoptions=["translation.*"])
    option, args = parser.parse_args()
    print config
