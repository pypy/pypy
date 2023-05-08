"""
Test the hpy+distutils integration. Most of the relevant code is in
hpy/devel/__init__.py.

Note that this is a different kind of test than the majority of the other
files in this directory, which all inherit from HPyTest and test the API
itself.
"""

import sys
import os
import textwrap
import subprocess
import shutil
import venv
import py
import pytest

from test.support import atomic_run, HPY_ROOT

# ====== IMPORTANT DEVELOPMENT TIP =====
# You can use py.test --reuse-venv to speed up local testing.
#
# The env is created once in /tmp/venv-for-hpytest and reused among tests and
# sessions. If you want to recreate it, simply rm -r /tmp/venv-for-hpytest

def print_CalledProcessError(p):
    """
    Print all information about a CalledProcessError
    """
    print('========== subprocess failed ==========')
    print('command:', ' '.join(p.cmd))
    print('argv:   ', p.cmd)
    print('return code:', p.returncode)
    print()
    print('---------- <stdout> ----------')
    print(p.stdout.decode('latin-1'))
    print('---------- </stdout> ---------')
    print()
    print('---------- <stderr> ----------')
    print(p.stderr.decode('latin-1'))
    print('---------- </stderr> ---------')

@pytest.fixture(scope='session')
def venv_template(request, tmpdir_factory):
    if request.config.option.reuse_venv:
        d = py.path.local('/tmp/venv-for-hpytest')
        if d.check(dir=True):
            # if it exists, we assume it's correct. If you want to recreate,
            # just manually delete /tmp/venv-for-hpytest
            return d
    else:
        d = tmpdir_factory.mktemp('venv')

    venv.create(d, with_pip=True)

    # remove the scripts: they contains a shebang and it will fail subtly
    # after we clone the template. Yes, we could try to fix the shebangs, but
    # it's just easier to use e.g. python -m pip
    attach_python_to_venv(d)
    for script in d.bin.listdir():
        if script.basename.startswith('python'):
            continue
        script.remove()
    #
    try:
        atomic_run(
            [str(d.python), '-m', 'pip', 'install', '-U', 'pip', 'wheel', 'setuptools'],
            check=True,
            capture_output=True,
        )
        atomic_run(
            [str(d.python), '-m', 'pip', 'install', str(HPY_ROOT)],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as cpe:
        print_CalledProcessError(cpe)
        raise
    return d

def attach_python_to_venv(d):
    if os.name == 'nt':
        d.bin = d.join('Scripts')
    else:
        d.bin = d.join('bin')
    d.python = d.bin.join('python')


@pytest.mark.usefixtures('initargs')
class TestDistutils:

    @pytest.fixture()
    def initargs(self, pytestconfig, tmpdir, venv_template):
        self.tmpdir = tmpdir
        # create a fresh venv by copying the template
        self.venv = tmpdir.join('venv')
        shutil.copytree(venv_template, self.venv)
        attach_python_to_venv(self.venv)
        # create the files for our test project
        self.hpy_test_project = tmpdir.join('hpy_test_project').ensure(dir=True)
        self.gen_project()
        self.hpy_test_project.chdir()

    @pytest.fixture(params=['cpython', 'hybrid', 'universal'])
    def hpy_abi(self, request):
        return request.param

    def python(self, *args, capture=False):
        """
        Run python inside the venv; if capture==True, return stdout
        """
        cmd = [str(self.venv.python)] + list(args)
        print('[RUN]', ' '.join(cmd))
        if capture:
            proc = atomic_run(cmd, capture_output=True)
            out = proc.stdout.decode('latin-1').strip()
        else:
            proc = atomic_run(cmd)
            out = None
        proc.check_returncode()
        return out


    def writefile(self, fname, content):
        """
        Write a file inside hpy_test_project
        """
        f = self.hpy_test_project.join(fname)
        content = textwrap.dedent(content)
        f.write(content)

    def gen_project(self):
        """
        Generate the files needed to build the project, except setup.py
        """
        self.writefile('cpymod.c', """
            // the simplest possible Python/C module
            #include <Python.h>
            static PyModuleDef moduledef = {
                PyModuleDef_HEAD_INIT,
                "cpymod",
                "cpymod docstring"
            };

            PyMODINIT_FUNC
            PyInit_cpymod(void)
            {
                return PyModule_Create(&moduledef);
            }
        """)

        self.writefile('hpymod.c', """
            // the simplest possible HPy module
            #include <hpy.h>
            static HPyModuleDef moduledef = {
                .doc = "hpymod with HPy ABI: " HPY_ABI,
            };

            HPy_MODINIT(hpymod, moduledef)
        """)

        self.writefile('hpymod_legacy.c', """
            // the simplest possible HPy+legacy module
            #include <hpy.h>
            #include <Python.h>

            static PyObject *f(PyObject *self, PyObject *args)
            {
                return PyLong_FromLong(1234);
            }
            static PyMethodDef my_legacy_methods[] = {
                {"f", (PyCFunction)f, METH_NOARGS},
                {NULL}
            };

            static HPyModuleDef moduledef = {
                .doc = "hpymod_legacy with HPy ABI: " HPY_ABI,
                .legacy_methods = my_legacy_methods,
            };

            HPy_MODINIT(hpymod_legacy, moduledef)
        """)

    def gen_setup_py(self, src):
        preamble = textwrap.dedent("""
            from setuptools import setup, Extension
            cpymod = Extension("cpymod", ["cpymod.c"])
            hpymod = Extension("hpymod", ["hpymod.c"])
            hpymod_legacy = Extension("hpymod_legacy", ["hpymod_legacy.c"])
        """)
        src = preamble + textwrap.dedent(src)
        f = self.hpy_test_project.join('setup.py')
        f.write(src)

    def get_docstring(self, modname):
        cmd = f'import {modname}; print({modname}.__doc__)'
        return self.python('-c', cmd, capture=True)

    def test_cpymod_setup_install(self):
        # CPython-only project, no hpy at all. This is a baseline to check
        # that everything works even without hpy.
        self.gen_setup_py("""
            setup(name = "hpy_test_project",
                  ext_modules = [cpymod],
            )
        """)
        self.python('setup.py', 'install')
        doc = self.get_docstring('cpymod')
        assert doc == 'cpymod docstring'

    def test_cpymod_with_empty_hpy_ext_modules_setup_install(self):
        # if we have hpy_ext_modules=[] we trigger the hpy.devel monkey
        # patch. This checks that we don't ext_modules still works after that.
        self.gen_setup_py("""
            setup(name = "hpy_test_project",
                  ext_modules = [cpymod],
                  hpy_ext_modules = []
            )
        """)
        self.python('setup.py', 'install')
        doc = self.get_docstring('cpymod')
        assert doc == 'cpymod docstring'

    def test_hpymod_py_stub(self):
        # check that that we generated the .py stub for universal
        self.gen_setup_py("""
            setup(name = "hpy_test_project",
                  hpy_ext_modules = [hpymod],
            )
        """)
        self.python('setup.py', '--hpy-abi=universal', 'build')
        build = self.hpy_test_project.join('build')
        lib = build.listdir('lib*')[0]
        hpymod_py = lib.join('hpymod.py')
        assert hpymod_py.check(exists=True)
        assert 'This file is automatically generated by hpy' in hpymod_py.read()

    def test_hpymod_build_platlib(self):
        # check that if we have only hpy_ext_modules, the distribution is
        # detected as "platform-specific" and not "platform-neutral". In
        # particular, we want the end result to be in
        # e.g. build/lib.linux-x86_64-3.8 and NOT in build/lib.
        self.gen_setup_py("""
            setup(name = "hpy_test_project",
                  hpy_ext_modules = [hpymod],
            )
        """)
        self.python('setup.py', 'build')
        build = self.hpy_test_project.join('build')
        libs = build.listdir('lib*')
        assert len(libs) == 1
        libdir = libs[0]
        # this is something like lib.linux-x86_64-cpython-38
        assert libdir.basename != 'lib'

    def test_hpymod_build_ext_inplace(self, hpy_abi):
        # check that we can install hpy modules with setup.py build_ext -i
        self.gen_setup_py("""
            setup(name = "hpy_test_project",
                  hpy_ext_modules = [hpymod],
            )
        """)
        self.python('setup.py', f'--hpy-abi={hpy_abi}', 'build_ext', '--inplace')
        doc = self.get_docstring('hpymod')
        assert doc == f'hpymod with HPy ABI: {hpy_abi}'

    def test_hpymod_setup_install(self, hpy_abi):
        # check that we can install hpy modules with setup.py install
        self.gen_setup_py("""
            setup(name = "hpy_test_project",
                  hpy_ext_modules = [hpymod],
            )
        """)
        self.python('setup.py', f'--hpy-abi={hpy_abi}', 'install')
        doc = self.get_docstring('hpymod')
        assert doc == f'hpymod with HPy ABI: {hpy_abi}'

    def test_hpymod_wheel(self, hpy_abi):
        # check that we can build and install wheels
        self.gen_setup_py("""
            setup(name = "hpy_test_project",
                  hpy_ext_modules = [hpymod],
            )
        """)
        self.python('setup.py', f'--hpy-abi={hpy_abi}', 'bdist_wheel')
        dist = self.hpy_test_project.join('dist')
        whl = dist.listdir('*.whl')[0]
        self.python('-m', 'pip', 'install', str(whl))
        doc = self.get_docstring('hpymod')
        assert doc == f'hpymod with HPy ABI: {hpy_abi}'

    def test_dont_mix_cpython_and_universal_abis(self):
        """
        See issue #322
        """
        # make sure that the build dirs for cpython and universal ABIs are
        # distinct
        self.gen_setup_py("""
            setup(name = "hpy_test_project",
                  hpy_ext_modules = [hpymod],
                  install_requires = [],
            )
        """)
        self.python('setup.py', 'install')
        # in the build/ dir, we should have 2 directories: temp and lib
        build = self.hpy_test_project.join('build')
        temps = build.listdir('temp*')
        libs = build.listdir('lib*')
        assert len(temps) == 1
        assert len(libs) == 1
        #
        doc = self.get_docstring('hpymod')
        assert doc == 'hpymod with HPy ABI: cpython'

        # now recompile with universal *without* cleaning the build
        self.python('setup.py', '--hpy-abi=universal', 'install')
        # in the build/ dir, we should have 4 directories: 2 temp*, and 2 lib*
        build = self.hpy_test_project.join('build')
        temps = build.listdir('temp*')
        libs = build.listdir('lib*')
        assert len(temps) == 2
        assert len(libs) == 2
        #
        doc = self.get_docstring('hpymod')
        assert doc == 'hpymod with HPy ABI: universal'

    def test_hpymod_legacy(self, hpy_abi):
        if hpy_abi == 'universal':
            pytest.skip('only for cpython and hybrid ABIs')
        self.gen_setup_py("""
            setup(name = "hpy_test_project",
                  hpy_ext_modules = [hpymod_legacy],
                  install_requires = [],
            )
        """)
        self.python('setup.py', 'install')
        src = 'import hpymod_legacy; print(hpymod_legacy.f())'
        out = self.python('-c', src, capture=True)
        assert out == '1234'

    def test_hpymod_legacy_fails_with_universal(self):
        self.gen_setup_py("""
            setup(name = "hpy_test_project",
                  hpy_ext_modules = [hpymod_legacy],
                  install_requires = [],
            )
        """)
        with pytest.raises(subprocess.CalledProcessError) as exc:
            self.python('setup.py', '--hpy-abi=universal', 'install', capture=True)
        expected_msg = ("It is forbidden to #include <Python.h> when "
                        "targeting the HPy Universal ABI")

        # gcc/clang prints the #error on stderr, MSVC prints it on
        # stdout. Here we check that the error is printed "somewhere", we
        # don't care exactly where.
        out = exc.value.stdout + b'\n' + exc.value.stderr
        out = out.decode('latin-1')
        if expected_msg not in out:
            print_CalledProcessError(exc.value)
        assert expected_msg in out
