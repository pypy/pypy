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

                              
pypy_optiondescription = OptionDescription("pypy", "All PyPy Options", [
    OptionDescription("objspace", "Object Space Option", [
        ChoiceOption("name", "Object Space name",
                     ["std", "flow", "logic", "thunk", "cpy", "dump", "sand"],
                     "std",
                     requires = {
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


    ]),

    BoolOption("translating", "indicates whether we are translating currently",
               default=False, cmdline=None),

    OptionDescription("translation", "Translation Options", [
        BoolOption("stackless", "compile stackless features in",
                   default=False, cmdline="--stackless",
                   requires=[("translation.type_system", "lltype")]),
        ChoiceOption("type_system", "Type system to use when RTyping",
                     ["lltype", "ootype"], cmdline=None),
        ChoiceOption("backend", "Backend to use for code generation",
                     ["c", "llvm", "cli", "js", "squeak", "cl"],
                     requires={
                         "c":      [("translation.type_system", "lltype")],
                         "llvm":   [("translation.type_system", "lltype"),
                                    ("translation.gc", "boehm"),
                                    ("translation.backendopt.raisingop2direct_call", True)],
                         "cli":    [("translation.type_system", "ootype")],
                         "js":     [("translation.type_system", "ootype")],
                         "squeak": [("translation.type_system", "ootype")],
                         "cl":     [("translation.type_system", "ootype")],
                         },
                     cmdline="-b --backend"),
        ChoiceOption("gc", "Garbage Collection Strategy",
                     ["boehm", "ref", "framework", "none", "stacklessgc",
                      "exact_boehm"],
                      "boehm", requires={
                         "stacklessgc": [("translation.stackless", True)]},
                      cmdline="--gc"),
        BoolOption("thread", "enable use of threading primitives",
                   default=False, cmdline="--thread"),
        BoolOption("verbose", "Print extra information", default=False),
        BoolOption("debug", "Record extra annotation information",
                   cmdline="-d --debug", default=False),
        BoolOption("insist", "Try hard to go on RTyping", default=False,
                   cmdline="--insist"),
        BoolOption("countmallocs", "Count mallocs and frees", default=False,
                   cmdline=None),

        # misc
        StrOption("cc", "Specify compiler", cmdline="--cc"),
        StrOption("profopt", "Specify profile based optimization script",
                  cmdline="--profopt"),
        BoolOption("debug_transform", "Perform the debug transformation",
                   default=False, cmdline="--debug-transform", negation=False),

        BoolOption("instrument", "internal: turn instrumentation on",
                   default=False, cmdline=None),

        ArbitraryOption("instrumentctl", "internal",
                   default=None),        

        # portability options
        BoolOption("vanilla",
                   "Try to be as portable as possible, which is not much",
                   default=False,
                   cmdline="--vanilla",
                   requires=[("translation.no__thread", True)]),
        BoolOption("no__thread",
                   "don't use __thread for implementing TLS",
                   default=False, cmdline="--no__thread", negation=False),
        StrOption("compilerflags", "Specify flags for the compiler", 
                   cmdline="--cflags"),
        StrOption("linkerflags", "Specify flags for the linker", 
                   cmdline="--ldflags"),

        # Flags of the TranslationContext:
        BoolOption("simplifying", "Simplify flow graphs", default=True),
        BoolOption("do_imports_immediately", "XXX", default=True,
                   cmdline=None),
        BoolOption("builtins_can_raise_exceptions", "XXX", default=False,
                   cmdline=None),
        BoolOption("list_comprehension_operations", "XXX", default=False,
                   cmdline=None),
        ChoiceOption("fork_before",
                     "(UNIX) Create restartable checkpoint before step",
                     ["annotate", "rtype", "backendopt", "database", "source",
                      "hintannotate"],
                     default=None, cmdline="--fork-before"),

        OptionDescription("backendopt", "Backend Optimization Options", [
            BoolOption("print_statistics", "Print statistics while optimizing",
                       default=False),
            BoolOption("merge_if_blocks", "Merge if ... elif chains",
                       cmdline="--if-block-merge", default=True),
            BoolOption("raisingop2direct_call",
                       "Transform exception raising operations",
                       default=False, cmdline="--raisingop2direct_call"),
            BoolOption("mallocs", "Remove mallocs", default=True),
            BoolOption("constfold", "Constant propagation",
                       default=True),
            BoolOption("heap2stack", "Escape analysis and stack allocation",
                       default=False,
                       requires=[("translation.stackless", False)]),
            BoolOption("clever_malloc_removal",
                       "Remove mallocs in a clever way", default=False),
            BoolOption("remove_asserts",
                       "Kill 'raise AssertionError', which lets the C "
                       "optimizer remove the asserts", default=False),
            IntOption("inline_threshold", "Threshold when to inline functions",
                      default=1, cmdline=None),
            StrOption("profile_based_inline",
                      "Use call count profiling to drive inlining"
                      ", specify arguments",
                      default=None, cmdline="--prof-based-inline"),
        ]),

        OptionDescription("cli", "GenCLI options", [
            BoolOption("trace_calls", "Trace function calls", default=False,
                       cmdline="--cli-trace-calls")
        ]),
    ]),
])


if __name__ == '__main__':
    config = Config(pypy_optiondescription)
    print config.getpaths()
    parser = to_optparse(config) #, useoptions=["translation.*"])
    option, args = parser.parse_args()
    print config
