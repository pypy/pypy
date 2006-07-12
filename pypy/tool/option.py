# This is where the options for py.py are defined.
# XXX needs clean-up and reorganization.

import os
import optparse
make_option = optparse.make_option

class Options:
    showwarning = 0
    objspace = "std" 
    oldstyle = 0
    uselibfile = 0
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
    options = []

    def usemodules_callback(option, opt, value, parser): 
        parser.values.usemodules.append(value) 
        
    options.append(make_option(
        '-o', '--objspace', action="store", type="string", dest="objspace", 
        help="object space to run PyPy on."))
    options.append(make_option(
        '--usemodules', action="callback", metavar='NAME',
        callback=usemodules_callback,  type="string",
        help="(mixed) modules to use."))
    options.append(make_option(
        '--oldstyle', action="store_true", dest="oldstyle",
        help="enable oldstyle classes as default metaclass (std objspace only)"))
    options.append(make_option(
        '--uselibfile', action="store_true", dest="uselibfile",
        help="enable our custom file implementation"))
    options.append(make_option(
        '--nofaking', action="store_true", dest="nofaking",
        help="avoid faking of modules or objects"))
    options.append(make_option(
        '-w', action="store_true", dest="showwarning",
        help="enable warnings (disabled by default)"))
    options.append(make_option(
        '-H', action="callback",
        callback=run_tb_server,
        help="use web browser for traceback info"))
    options.append(make_option(
        '--compiler', action="store", type="string", dest="compiler",
        default=None,
        help="""select compiling approach. see pypy/doc/README.compiling""",
        metavar="[ast|cpython]")) 
    options.append(make_option(
        '--parser', action="store",type="string", dest="parser", default=None,
        help="select the parser module to use",
        metavar="[pypy|cpython]"))
## for this to work the option module need to be loaded before the grammar!
##     options.append(make_option(
##         '--version', action="store",type="string", dest="version",
##         help="select the Python version to emulate",
##         metavar="[native|2.3|2.4]"))

    return options

def process_options(optionlist, input_options, argv=None):
    global Options
    Options = input_options
    op = optparse.OptionParser()
    op.add_options(optionlist)
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
    if (getattr(cmdlineopt, "uselibfile", False) or
        kwds.get("uselibfile", False)):
        conf.objspace.uselibfile = True
    if getattr(cmdlineopt, "oldstyle", False) or kwds.get("oldstyle", False):
        conf.objspace.oldstyle = True
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

