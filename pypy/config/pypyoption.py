import py
from pypy.config.config import OptionDescription, BoolOption, IntOption
from pypy.config.config import ChoiceOption, to_optparse, Config

modulepath = py.magic.autopath().dirpath().dirpath().join("module")
all_modules = [p.basename for p in modulepath.listdir()
                   if p.check(dir=True, dotfile=False)]

default_modules = dict.fromkeys(
    ["unicodedata", "_codecs", "gc", "_weakref", "array", "marshal", "errno",
     "math", "_sre", "_pickle_support", "sys", "exceptions", "__builtins__",
     "recparser", "symbol"])
                              
pypy_optiondescription = OptionDescription("pypy", [
    OptionDescription("objspace", [
        ChoiceOption("name", "Object Space name",
                     ["std", "flow", "logic", "thunk", "cpy"], "std",
                     cmdline='--objspace -o'),

        ChoiceOption("parser", "parser",
                     ["pypy", "cpython"], "pypy"),

        ChoiceOption("compiler", "compiler",
                     ["cpython", "ast"], "ast"),

        BoolOption("nofaking", "disallow faking in the object space",
                   default=False,
                   requires=[
                       ("uselibfile", True),
                       ("usemodules.posix", True),
                       ("usemodules.time", True),
                       ("usemodules.errno", True)]),

        BoolOption("uselibfile", "use the applevel file implementation",
                   default=False),

        OptionDescription("usemodules", [
            BoolOption(modname, "use module %s" % (modname, ),
                       default=modname in default_modules)
            for modname in all_modules]),

        BoolOption("geninterp", "specify whether geninterp should be used"),

       
        OptionDescription("std", [
            BoolOption("withsmallint", "use tagged integers",
                       default=False),

            BoolOption("withprebuiltint", "prebuilt commonly used int objects",
                       default=False, requires=[("withsmallint", False)]),

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

            BoolOption("oldstyle",
                       "specify whether the default metaclass should be classobj",
                       default=False),
         ]),


    ]),

    BoolOption("translating", "indicates whether we are translating currently",
               default=False),
])

if __name__ == '__main__':
    config = Config(pypy_optiondescription)
    parser = to_optparse(config, ["objspace.name",
                                  "objspace.std.*",
                                  "objspace.std.withsmallint",
                                  "objspace.std.withprebuiltint",
                                  "objspace.usemodules",
                                  "objspace.std.prebuiltintfrom",])
    option, args = parser.parse_args()
    print config
