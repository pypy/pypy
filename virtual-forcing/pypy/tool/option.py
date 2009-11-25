# This is where the options for py.py are defined.

import os
from pypy.config.pypyoption import get_pypy_config
from pypy.config.config import Config, OptionDescription, to_optparse
import optparse

extra_useage = """For detailed descriptions of all the options see
http://codespeak.net/pypy/dist/pypy/doc/config/commandline.html"""

def run_tb_server(option, opt, value, parser):
    from pypy.tool import tb_server
    tb_server.start()

def get_standard_options():
    config = get_pypy_config()
    parser = to_optparse(config, useoptions=["objspace.*"],
                         extra_useage=extra_useage)
    parser.add_option(
        '-H', action="callback",
        callback=run_tb_server,
        help="use web browser for traceback info")
    return config, parser

def process_options(parser, argv=None):
    parser.disable_interspersed_args()
    options, args = parser.parse_args(argv)
    return args

def make_config(cmdlineopt, **kwds):
    """ make a config from cmdline options (which overrides everything)
    and kwds """

    config = get_pypy_config(translating=False)
    objspace = kwds.pop("objspace", None)
    if objspace is not None:
        config.objspace.name = objspace
    for modname in kwds.pop("usemodules", []):
        setattr(config.objspace.usemodules, modname, True)
    config.set(**kwds)
    return config

def make_objspace(config):
    mod = __import__('pypy.objspace.%s' % config.objspace.name,
                     None, None, ['Space'])
    Space = mod.Space
    #conf.objspace.logbytecodes = True
    space = Space(config)
    return space

