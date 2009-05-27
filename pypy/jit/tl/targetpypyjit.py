from pypy.config.config import to_optparse, SUPPRESS_USAGE

take_options = True


def readfile(filename):
    import os
    fd = os.open(filename, os.O_RDONLY, 0)
    blocks = []
    while True:
        data = os.read(fd, 4096)
        if not data:
            break
        blocks.append(data)
    os.close(fd)
    return ''.join(blocks)

def entry_point(args):
    from pypy.interpreter.pycode import PyCode
    if len(args) > 1:
        filename = args[1]
        func_to_run = space.wrap(args[2])
    else:
        filename = 'pypyjit_demo.py'
        func_to_run = None
    source = readfile(filename)
    ec = space.getexecutioncontext()
    code = ec.compiler.compile(source, '?', 'exec', 0)
    assert isinstance(code, PyCode)
    code.exec_code(space, w_dict, w_dict)
    if func_to_run is not None:
        space.call_function(space.getitem(w_dict, func_to_run))
    return 0

def opt_parser(config):
    parser = to_optparse(config, useoptions=["objspace.*"],
                         parserkwargs={'usage': SUPPRESS_USAGE})
    return parser

def handle_config(config, translateconfig):
    config.translation.backendopt.inline_threshold = 0   # XXX
    config.translation.rweakref = False     # XXX
    # set up the objspace optimizations based on the --opt argument
    from pypy.config.pypyoption import set_pypy_opt_level
    set_pypy_opt_level(config, translateconfig.opt)

def get_additional_config_options():
    from pypy.config.pypyoption import pypy_optiondescription
    return pypy_optiondescription

def target(driver, args):
    from pypy.tool.option import make_objspace
    from pypy.translator.goal.ann_override import PyPyAnnotatorPolicy
    from pypy.objspace.std import multimethod
    global space, w_dict
    #
    config = driver.config
    assert config.translation.jit, "you forgot the '--jit' option :-)"
    parser = opt_parser(config)
    parser.parse_args(args)
    #
    config.objspace.compiler = 'ast'
    config.objspace.nofaking = True
    config.objspace.allworkingmodules = False
    config.objspace.usemodules.pypyjit = True
    config.objspace.usemodules._weakref = False
    config.objspace.usemodules._sre = False
    if config.translation.type_system == 'lltype':
        config.objspace.std.multimethods = 'mrd'
        multimethod.Installer = multimethod.InstallerVersion2
    else:
        from pypy.rlib import jit
        jit.PARAMETERS['hash_bits'] = 6 # XXX: this is a hack, should be fixed at some point
        config.objspace.std.multimethods = 'doubledispatch'
        multimethod.Installer = multimethod.InstallerVersion1
        
    config.objspace.std.builtinshortcut = True
    config.objspace.opcodes.CALL_LIKELY_BUILTIN = True
    config.objspace.std.withrangelist = True
    #
    print config
    space = make_objspace(config)
    w_dict = space.newdict()
    return entry_point, None, PyPyAnnotatorPolicy(single_space = space)


def jitpolicy(driver):
    """Returns the JIT policy to use when translating."""
    from pypy.module.pypyjit.policy import PyPyJitPolicy
    return PyPyJitPolicy(driver.translator)
