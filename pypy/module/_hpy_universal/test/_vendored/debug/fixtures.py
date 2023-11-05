from _pytest.tmpdir import TempdirFactory
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import (unwrap_spec, interp2app)
from pypy.interpreter.typedef import TypeDef
from pypy.module._hpy_universal.test._vendored.support import ExtensionCompiler
from pypy.module._hpy_universal import llapi
from pypy.module._hpy_universal._vendored.hpy.devel import HPyDevel

COMPILER_VERBOSE = False
hpy_abi = 'debug'

class W_ExtensionCompiler(W_Root):
    def __init__(self, compiler):
        self.compiler = compiler

    @staticmethod
    def descr_new(space, w_type):
        return W_ExtensionCompiler()

    @unwrap_spec(main_src='text', name='text', w_extra_sources=W_Root, hpy_abi='text')
    def descr_make_module(self, space, main_src, name='mytest',
                            w_extra_sources=None, hpy_abi=hpy_abi):
        if w_extra_sources is None:
            extra_sources = ()
        else:
            items_w = space.unpackiterable(w_extra_sources)
            extra_sources = [space.text_w(item) for item in items_w]
        module = self.compiler.compile_module(
            main_src, self.compiler.ExtensionTemplate, name, extra_sources)
        if hpy_abi in ("debug", "hybrid+debug"):
            mode = llapi.MODE_DEBUG
        elif hpy_abi in ("universal", "hybrid"):
            mode = llapi.MODE_UNIVERSAL
        elif hpy_abi == "trace":
            mode = llapi.MODE_TRACE
        else:
            mode = -1
        w_mod = space.appexec([space.newtext(name),
                               space.newtext(module.so_filename),
                               space.newint(mode)],
            """(name, so_filename, mode):
                import sys
                import _hpy_universal
                import importlib.util
                assert name not in sys.modules
                spec = importlib.util.spec_from_file_location(name, so_filename)
                mod = _hpy_universal.load(name, so_filename, spec, mode=mode)
                mod.__file__ = so_filename
                mod.__spec__ = spec
                return mod
            """
        )
        return w_mod

W_ExtensionCompiler.typedef = TypeDef("ExtensionCompiler",
    #'__new__'=interp2app(W_ExtensionCompiler.descr_new),
    make_module=interp2app(W_ExtensionCompiler.descr_make_module),
)

def compiler(space, config):
    hpy_abi = 'debug'
    hpy_devel = HPyDevel(str(llapi.BASE_DIR))
    if space.config.objspace.usemodules.cpyext:
        from pypy.module import cpyext
        cpyext_include_dirs = cpyext.api.include_dirs
    else:
        cpyext_include_dirs = None
    tmpdir = TempdirFactory(config).getbasetemp()
    compiler =  ExtensionCompiler(tmpdir, hpy_devel, hpy_abi,
                             compiler_verbose=COMPILER_VERBOSE,
                            extra_include_dirs=cpyext_include_dirs)
    w_compiler = W_ExtensionCompiler(compiler)
    return w_compiler
