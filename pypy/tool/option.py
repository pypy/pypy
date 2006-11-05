# This is where the options for py.py are defined.
# XXX needs clean-up and reorganization.

import os
from pypy.config.pypyoption import pypy_optiondescription
from pypy.config.config import Config, OptionDescription, to_optparse
from py.compat import optparse
make_option = optparse.make_option

class Options:
    objspace = "std" 
    oldstyle = 0
    nofaking = 0
    parser = "pypy" # "cpython" / "pypy" 
    compiler = "ast" 
         # "ast" uses interpreter/pyparser & interpreter/astcompiler.py 
         # "cpython" uses cpython parser and cpython c-level compiler 
    usemodules = []
    version = "2.5a" # "native" / "2.3" / "2.4" / "2.5a"

def run_tb_server(option, opt, value, parser):
    from pypy.tool import tb_server
    tb_server.start()

 
def get_standard_options():
    config = Config(pypy_optiondescription)
    parser = to_optparse(config, useoptions=["objspace.*"])
    parser.add_option(
        '-H', action="callback",
        callback=run_tb_server,
        help="use web browser for traceback info")
    return config, parser

def process_options(op, input_options, argv=None):
    global Options
    Options = input_options
    # backward compatilibity
    if isinstance(op, list):
        import sys, os
        basename = os.path.basename(sys.argv[0])
        config = Config(OptionDescription(basename, basename, []))
        parser = to_optparse(config)
        parser.add_options(op)
        op = parser
    op.disable_interspersed_args()
    options, args = op.parse_args(argv, input_options)
    return args

def make_config(cmdlineopt, **kwds):
    """ make a config from cmdline options (which overrides everything)
    and kwds """

    # XXX this whole file should sooner or later go away and the cmd line
    # options be generated from the option description. it's especially messy
    # since we have to check whether the default was actually overwritten
    from pypy.config.pypyoption import pypy_optiondescription
    from pypy.config.config import Config
    conf = Config(pypy_optiondescription)
    if kwds.get("objspace", None) is not None:
        conf.objspace.name = kwds["objspace"]
    if getattr(cmdlineopt, "objspace", None) is not None:
        conf.objspace.name = cmdlineopt.objspace
    modnames = getattr(cmdlineopt, "usemodules", '')
    if isinstance(modnames, str):
        modnames = [mn.strip() for mn in modnames.split(',') if mn.strip()]
    for modname in modnames:
        setattr(conf.objspace.usemodules, modname, True)
    for modname in kwds.get("usemodules", []):
        setattr(conf.objspace.usemodules, modname, True)
    if getattr(cmdlineopt, "nofaking", False) or kwds.get("nofaking", False):
        conf.objspace.nofaking = True
    if getattr(cmdlineopt, "oldstyle", False) or kwds.get("oldstyle", False):
        conf.objspace.std.oldstyle = True
    if hasattr(cmdlineopt, "parser") and cmdlineopt.parser is not None:
        conf.objspace.parser = cmdlineopt.parser
    if kwds.get("compiler") is not None:
        conf.obspace.compiler = kwds['compiler']
    if getattr(cmdlineopt, "compiler", None) is not None:
        conf.objspace.compiler = cmdlineopt.compiler
    for names, value in kwds.iteritems():
        if "." not in names:
            continue
        names = names.split(".")
        subconf = conf
        for name in names[:-1]:
            subconf = getattr(subconf, name)
        setattr(subconf, names[-1], value)
    return conf

def make_objspace(conf):
    mod = __import__('pypy.objspace.%s' % conf.objspace.name,
                     None, None, ['Space'])
    Space = mod.Space
    #conf.objspace.logbytecodes = True
    space = Space(conf) 
    return space 

