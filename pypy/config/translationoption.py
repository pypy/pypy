import autopath
import py, os
from pypy.config.config import OptionDescription, BoolOption, IntOption, ArbitraryOption
from pypy.config.config import ChoiceOption, StrOption, to_optparse, Config

translation_optiondescription = OptionDescription(
        "translation", "Translation Options", [
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
    BoolOption("llvm_via_c", "compile llvm bytecode via C",
               default=False, cmdline="--llvm-via-c",
               requires=[("translation.backend", "llvm")]),
    ChoiceOption("gc", "Garbage Collection Strategy",
                 ["boehm", "ref", "framework", "none", "stacklessgc",
                  "exact_boehm"],
                  "ref", requires={
                     "stacklessgc": [("translation.stackless", True)]},
                  cmdline="--gc"),
    BoolOption("thread", "enable use of threading primitives",
               default=False, cmdline="--thread"),
    BoolOption("verbose", "Print extra information", default=False),
    BoolOption("debug", "Record extra annotation information",
               cmdline="-d --debug", default=False),
    BoolOption("insist", "Try hard to go on RTyping", default=False,
               cmdline="--insist"),
    IntOption("withsmallfuncsets",
              "Represent groups of less funtions than this as indices into an array",
               default=0),
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
    BoolOption("builtins_can_raise_exceptions", "XXX", default=False,
               cmdline=None),
    BoolOption("list_comprehension_operations", "XXX", default=False,
               cmdline=None),
    ChoiceOption("fork_before",
                 "(UNIX) Create restartable checkpoint before step",
                 ["annotate", "rtype", "backendopt", "database", "source",
                  "hintannotate", "timeshift"],
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
])

def get_combined_translation_config(other_optdescr=None,
                                    existing_config=None,
                                    overrides=None,
                                    translating=False):
    if overrides is None:
        overrides = {}
    d = BoolOption("translating",
                   "indicates whether we are translating currently",
                   default=False, cmdline=None)
    if other_optdescr is None:
        children = []
        newname = ""
    else:
        children = [other_optdescr]
        newname = other_optdescr._name
    if existing_config is None:
        children += [d, translation_optiondescription]
    else:
        children += [child for child in existing_config._cfgimpl_descr._children
                         if child._name != newname]
    descr = OptionDescription("pypy", "all options", children)
    config = Config(descr, **overrides)
    if translating:
        config.translating = True
    if existing_config is not None:
        for child in existing_config._cfgimpl_descr._children:
            if child._name == newname:
                continue
            value = getattr(existing_config, child._name)
            config._cfgimpl_values[child._name] = value
    return config
