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
    source = readfile('pypyjit_demo.py')
    ec = space.getexecutioncontext()
    code = ec.compiler.compile(source, '?', 'exec', 0)
    assert isinstance(code, PyCode)
    code.exec_code(space, w_dict, w_dict)
    return 0

def opt_parser(config):
    parser = to_optparse(config, useoptions=["objspace.*"],
                         parserkwargs={'usage': SUPPRESS_USAGE})
    return parser

def handle_config(config, translateconfig):
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
    config.objspace.std.multimethods = 'mrd'
    multimethod.Installer = multimethod.InstallerVersion2
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
