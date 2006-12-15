# Test the runpy module
import unittest
import os
import os.path
import sys
import tempfile
from pypy.lib.runpy import _run_module_code, run_module


verbose = 0

# Set up the test code and expected results
class TestRunModuleCode:

    expected_result = ["Top level assignment", "Lower level reference"]
    test_source = (
        "# Check basic code execution\n"
        "result = ['Top level assignment']\n"
        "def f():\n"
        "    result.append('Lower level reference')\n"
        "f()\n"
        "# Check the sys module\n"
        "import sys\n"
        "run_argv0 = sys.argv[0]\n"
        "if __name__ in sys.modules:\n"
        "    run_name = sys.modules[__name__].__name__\n"
        "# Check nested operation\n"
        "import pypy.lib.runpy\n"
        "nested = pypy.lib.runpy._run_module_code('x=1\\n', mod_name='<run>',\n"
        "                                          alter_sys=True)\n"
    )


    def test_run_module_code(self):
        initial = object()
        name = "<Nonsense>"
        file = "Some other nonsense"
        loader = "Now you're just being silly"
        d1 = dict(initial=initial)
        saved_argv0 = sys.argv[0]
        d2 = _run_module_code(self.test_source,
                              d1,
                              name,
                              file,
                              loader,
                              True)
        assert "result" not in d1
        assert d2["initial"] is initial
        assert d2["result"] == self.expected_result
        assert d2["nested"]["x"] == 1
        assert d2["__name__"] is name
        assert d2["run_name"] is name
        assert d2["__file__"] is file
        assert d2["run_argv0"] is file
        assert d2["__loader__"] is loader
        assert sys.argv[0] is saved_argv0
        assert name not in sys.modules

    def test_run_module_code_defaults(self):
        saved_argv0 = sys.argv[0]
        d = _run_module_code(self.test_source)
        assert d["result"] == self.expected_result
        assert d["__name__"] is None
        assert d["__file__"] is None
        assert d["__loader__"] is None
        assert d["run_argv0"] is saved_argv0
        assert "run_name" not in d
        assert sys.argv[0] is saved_argv0

class TestRunModule:

    def expect_import_error(self, mod_name):
        try:
            run_module(mod_name)
        except ImportError:
            pass
        else:
            assert false, "Expected import error for " + mod_name

    def test_invalid_names(self):
        self.expect_import_error("sys")
        self.expect_import_error("sys.imp.eric")
        self.expect_import_error("os.path.half")
        self.expect_import_error("a.bee")
        self.expect_import_error(".howard")
        self.expect_import_error("..eaten")

    def test_library_module(self):
        run_module("pypy.lib.runpy")

    def _make_pkg(self, source, depth):
        pkg_name = "__runpy_pkg__"
        init_fname = "__init__"+os.extsep+"py"
        test_fname = "runpy_test"+os.extsep+"py"
        pkg_dir = sub_dir = tempfile.mkdtemp()
        if verbose: print "  Package tree in:", sub_dir
        sys.path.insert(0, pkg_dir)
        if verbose: print "  Updated sys.path:", sys.path[0]
        for i in range(depth):
            sub_dir = os.path.join(sub_dir, pkg_name)
            os.mkdir(sub_dir)
            if verbose: print "  Next level in:", sub_dir
            pkg_fname = os.path.join(sub_dir, init_fname)
            pkg_file = open(pkg_fname, "w")
            pkg_file.write("__path__ = ['%s']\n" % sub_dir)
            pkg_file.close()
            if verbose: print "  Created:", pkg_fname
        mod_fname = os.path.join(sub_dir, test_fname)
        mod_file = open(mod_fname, "w")
        mod_file.write(source)
        mod_file.close()
        if verbose: print "  Created:", mod_fname
        mod_name = (pkg_name+".")*depth + "runpy_test"
        return pkg_dir, mod_fname, mod_name

    def _del_pkg(self, top, depth, mod_name):
        for root, dirs, files in os.walk(top, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(top)
        if verbose: print "  Removed package tree"
        for i in range(depth+1): # Don't forget the module itself
            parts = mod_name.rsplit(".", i)
            entry = parts[0]
            del sys.modules[entry]
        if verbose: print "  Removed sys.modules entries"
        del sys.path[0]
        if verbose: print "  Removed sys.path entry"

    def _check_module(self, depth):
        pkg_dir, mod_fname, mod_name = (
               self._make_pkg("x=1\n", depth))
        try:
            if verbose: print "Running from source:", mod_name
            d1 = run_module(mod_name) # Read from source
            __import__(mod_name)
            os.remove(mod_fname)
            if verbose: print "Running from compiled:", mod_name
            d2 = run_module(mod_name) # Read from bytecode
        finally:
            self._del_pkg(pkg_dir, depth, mod_name)
        assert d1["x"] == d2["x"] == 1
        if verbose: print "Module executed successfully"

    def test_run_module(self):
        for depth in range(4):
            if verbose: print "Testing package depth:", depth
            self._check_module(depth)

