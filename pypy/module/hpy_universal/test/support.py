import py
import pytest
from rpython.tool.udir import udir
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.module.hpy_universal.llapi import INCLUDE_DIR
from pypy.module.hpy_universal._vendored.test import support as _support



class ExtensionCompiler(object):
    def __init__(self, base_dir):
        self.base_dir = base_dir

    def get_builddir(self, name='mytest'):
        builddir = py.path.local.make_numbered_dir(
            rootdir=py.path.local(self.base_dir),
            prefix=name + '-',
            keep=0)  # keep everything
        return builddir


class HPyTest(object):
    def setup_class(cls):
        if cls.runappdirect:
            pytest.skip()
        cls.compiler = ExtensionCompiler(udir)

        w_FakeSpec = cls.space.appexec([], """():
            class FakeSpec:
                def __init__(self, name, origin):
                    self.name = name
                    self.origin = origin
            return FakeSpec
        """)

        @unwrap_spec(source_template='text', name='text')
        def descr_make_module(space, source_template, name='mytest'):
            source = _support.expand_template(source_template, name)
            tmpdir = cls.compiler.get_builddir()
            filename = tmpdir.join(name+ '.c')
            filename.write(source)
            #
            ext = _support.get_extension(str(filename), name, include_dirs=[INCLUDE_DIR],
                                extra_compile_args=['-Wfatal-errors', '-g', '-Og'],
                                extra_link_args=['-g'])
            so_filename = _support.c_compile(str(tmpdir), ext, compiler_verbose=False,
                                    universal_mode=True)
            #
            w_mod = space.appexec(
                [w_FakeSpec, space.newtext(so_filename), space.newtext(name)],
                """(FakeSpec, path, modname):
                    from hpy_universal import load_from_spec
                    return load_from_spec(FakeSpec(modname, path))
                """
            )
            return w_mod
        cls.w_make_module = cls.space.wrap(interp2app(descr_make_module))

