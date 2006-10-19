import autopath
import py
from pypy.config.config import OptionDescription, BoolOption, IntOption
from pypy.config.config import ChoiceOption, to_optparse, Config

modulepath = py.magic.autopath().dirpath().dirpath().join("module")
all_modules = [p.basename for p in modulepath.listdir()
                   if p.check(dir=True, dotfile=False)]

default_modules = dict.fromkeys(
    [#"unicodedata",
     "_codecs", "gc", "_weakref", "array", "marshal", "errno",
     "math", "_sre", "_pickle_support", "sys", "exceptions", "__builtins__",
     "recparser", "symbol", "_random"])
                              
pypy_optiondescription = OptionDescription("pypy", "All PyPy Options", [
    OptionDescription("objspace", "Object Space Option", [
        ChoiceOption("name", "Object Space name",
                     ["std", "flow", "logic", "thunk", "cpy"], "std",
                     requires = {
                         "thunk": [("objspace.geninterp", False)],
                         "logic": [("objspace.geninterp", False)],
                     },
                     cmdline='--objspace -o'),

        ChoiceOption("parser", "parser",
                     ["pypy", "cpython"], "pypy",
                     cmdline='--parser'),

        ChoiceOption("compiler", "compiler",
                     ["cpython", "ast"], "ast",
                     cmdline='--compiler'),

        BoolOption("nofaking", "disallow faking in the object space",
                   default=False,
                   requires=[
                       ("objspace.uselibfile", True),
                       ("objspace.usemodules.posix", True),
                       ("objspace.usemodules.time", True),
                       ("objspace.usemodules.errno", True)],
                   cmdline='--nofaking'),

        BoolOption("uselibfile", "use the applevel file implementation",
                   default=False,
                   cmdline='--uselibfile'),

        OptionDescription("usemodules", "Which Modules should be used", [
            BoolOption(modname, "use module %s" % (modname, ),
                       default=modname in default_modules,
                       cmdline=None)
            for modname in all_modules], cmdline="--usemodules"),

        BoolOption("geninterp", "specify whether geninterp should be used"),

        BoolOption("logbytecodes",
                   "keep track of bytecode usage",
                   default=False),
       
        OptionDescription("std", "Standard Object Space Options", [
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


    ]),

    BoolOption("translating", "indicates whether we are translating currently",
               default=False, cmdline=None),
])


if __name__ == '__main__':
    config = Config(pypy_optiondescription)
    print config.getpaths()
    parser = to_optparse(config)
    option, args = parser.parse_args()
    print config
