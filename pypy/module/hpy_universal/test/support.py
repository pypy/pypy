import py
import pytest
from rpython.tool.udir import udir
from pypy.interpreter.gateway import interp2app, unwrap_spec, W_Root
from pypy.module.hpy_universal.llapi import INCLUDE_DIR
from pypy.module.hpy_universal._vendored.test import support as _support

COMPILER_VERBOSE = False

class HPyAppTest(object):

    @pytest.fixture
    def compiler(self):
        # see setup_method below
        return 'The fixture "compiler" is not used on pypy'

    @staticmethod
    def setup_class(cls):
        if cls.runappdirect:
            pytest.skip()

    def setup_method(self, meth):
        if self.space.config.objspace.usemodules.cpyext:
            from pypy.module import cpyext
            cpython_include_dirs = cpyext.api.include_dirs
        else:
            cpython_include_dirs = []
        #
        # it would be nice to use the 'compiler' fixture to provide
        # make_module as the std HPyTest do. Howwever, we don't have the space
        # yet, so it is much easier to prove make_module() here
        tmpdir = py.path.local.make_numbered_dir(rootdir=udir,
                                                 prefix=meth.__name__ + '-',
                                                 keep=0)  # keep everything
        compiler = _support.ExtensionCompiler(tmpdir, 'universal', INCLUDE_DIR,
                                              compiler_verbose=COMPILER_VERBOSE,
                                              cpython_include_dirs=cpython_include_dirs)
        #
        @unwrap_spec(source_template='text', name='text', w_extra_templates=W_Root)
        def descr_make_module(space, source_template, name='mytest',
                              w_extra_templates=None):
            if w_extra_templates is None:
                extra_templates = ()
            else:
                items_w = space.unpackiterable(w_extra_templates)
                extra_templates = [space.text_w(item) for item in items_w]
            so_filename = compiler.compile_module(source_template, name, extra_templates)
            w_mod = space.appexec([space.newtext(so_filename), space.newtext(name)],
                """(path, modname):
                    import hpy_universal
                    return hpy_universal.load(modname, path)
                """
            )
            return w_mod
        self.w_make_module = self.space.wrap(interp2app(descr_make_module))

        def should_check_refcount(space):
            return space.w_False
        self.w_should_check_refcount = self.space.wrap(interp2app(should_check_refcount))
