from contextlib import contextmanager
import linecache
import os
from io import StringIO
import re
import sys
import textwrap
import unittest
from test import support
from test.support.script_helper import assert_python_ok, assert_python_failure

from test.test_warnings.data import stacklevel as warning_tests

import warnings as original_warnings

py_warnings = support.import_fresh_module('warnings', blocked=['_warnings'])
c_warnings = support.import_fresh_module('warnings', fresh=['_warnings'])

Py_DEBUG = hasattr(sys, 'gettotalrefcount')

@contextmanager
def warnings_state(module):
    """Use a specific warnings implementation in warning_tests."""
    global __warningregistry__
    for to_clear in (sys, warning_tests):
        try:
            to_clear.__warningregistry__.clear()
        except AttributeError:
            pass
    try:
        __warningregistry__.clear()
    except NameError:
        pass
    original_warnings = warning_tests.warnings
    original_filters = module.filters
    try:
        module.filters = original_filters[:]
        module.simplefilter("once")
        warning_tests.warnings = module
        yield
    finally:
        warning_tests.warnings = original_warnings
        module.filters = original_filters


class TestWarning(Warning):
    pass


class BaseTest:

    """Basic bookkeeping required for testing."""

    def setUp(self):
        self.old_unittest_module = unittest.case.warnings
        # The __warningregistry__ needs to be in a pristine state for tests
        # to work properly.
        if '__warningregistry__' in globals():
            del globals()['__warningregistry__']
        if hasattr(warning_tests, '__warningregistry__'):
            del warning_tests.__warningregistry__
        if hasattr(sys, '__warningregistry__'):
            del sys.__warningregistry__
        # The 'warnings' module must be explicitly set so that the proper
        # interaction between _warnings and 'warnings' can be controlled.
        sys.modules['warnings'] = self.module
        # Ensure that unittest.TestCase.assertWarns() uses the same warnings
        # module than warnings.catch_warnings(). Otherwise,
        # warnings.catch_warnings() will be unable to remove the added filter.
        unittest.case.warnings = self.module
        super(BaseTest, self).setUp()

    def tearDown(self):
        sys.modules['warnings'] = original_warnings
        unittest.case.warnings = self.old_unittest_module
        super(BaseTest, self).tearDown()

class WarnTests(BaseTest):

    """Test warnings.warn() and warnings.warn_explicit()."""

    def test_missing_filename_not_main(self):
        # If __file__ is not specified and __main__ is not the module name,
        # then __file__ should be set to the module name.
        filename = warning_tests.__file__
        try:
            del warning_tests.__file__
            with warnings_state(self.module):
                with original_warnings.catch_warnings(record=True,
                        module=self.module) as w:
                    warning_tests.inner("spam8", stacklevel=1)
                    self.assertEqual(w[-1].filename, warning_tests.__name__)
        finally:
            warning_tests.__file__ = filename

    @unittest.skipUnless(hasattr(sys, 'argv'), 'test needs sys.argv')
    def test_missing_filename_main_with_argv(self):
        # If __file__ is not specified and the caller is __main__ and sys.argv
        # exists, then use sys.argv[0] as the file.
        filename = warning_tests.__file__
        module_name = warning_tests.__name__
        try:
            del warning_tests.__file__
            warning_tests.__name__ = '__main__'
            with warnings_state(self.module):
                with original_warnings.catch_warnings(record=True,
                        module=self.module) as w:
                    warning_tests.inner('spam9', stacklevel=1)
                    self.assertEqual(w[-1].filename, sys.argv[0])
        finally:
            warning_tests.__file__ = filename
            warning_tests.__name__ = module_name

    def test_missing_filename_main_without_argv(self):
        # If __file__ is not specified, the caller is __main__, and sys.argv
        # is not set, then '__main__' is the file name.
        filename = warning_tests.__file__
        module_name = warning_tests.__name__
        argv = sys.argv
        try:
            del warning_tests.__file__
            warning_tests.__name__ = '__main__'
            del sys.argv
            with warnings_state(self.module):
                with original_warnings.catch_warnings(record=True,
                        module=self.module) as w:
                    warning_tests.inner('spam10', stacklevel=1)
                    self.assertEqual(w[-1].filename, '__main__')
        finally:
            warning_tests.__file__ = filename
            warning_tests.__name__ = module_name
            sys.argv = argv

    def test_missing_filename_main_with_argv_empty_string(self):
        # If __file__ is not specified, the caller is __main__, and sys.argv[0]
        # is the empty string, then '__main__ is the file name.
        # Tests issue 2743.
        file_name = warning_tests.__file__
        module_name = warning_tests.__name__
        argv = sys.argv
        try:
            del warning_tests.__file__
            warning_tests.__name__ = '__main__'
            sys.argv = ['']
            with warnings_state(self.module):
                with original_warnings.catch_warnings(record=True,
                        module=self.module) as w:
                    warning_tests.inner('spam11', stacklevel=1)
                    self.assertEqual(w[-1].filename, '__main__')
        finally:
            warning_tests.__file__ = file_name
            warning_tests.__name__ = module_name
            sys.argv = argv

class PyWarnTests(WarnTests, unittest.TestCase):
    module = py_warnings


class _WarningsTests(BaseTest, unittest.TestCase):

    """Tests specific to the _warnings module."""

    module = c_warnings

    def test_filename_none(self):
        # issue #12467: race condition if a warning is emitted at shutdown
        globals_dict = globals()
        oldfile = globals_dict['__file__']
        try:
            catch = original_warnings.catch_warnings(record=True,
                                                     module=self.module)
            with catch as w:
                self.module.filterwarnings("always", category=UserWarning)
                globals_dict['__file__'] = None
                original_warnings.warn('test', UserWarning)
                self.assertTrue(len(w))
        finally:
            globals_dict['__file__'] = oldfile


class EnvironmentVariableTests(BaseTest):

    def test_conflicting_envvar_and_command_line(self):
        rc, stdout, stderr = assert_python_failure("-Werror::DeprecationWarning", "-c",
            "import sys, warnings; sys.stdout.write(str(sys.warnoptions)); "
            "warnings.warn('Message', DeprecationWarning)",
            PYTHONWARNINGS="default::DeprecationWarning",
            PYTHONDEVMODE="")
        self.assertEqual(stdout,
            b"['default::DeprecationWarning', 'error::DeprecationWarning']")
        self.assertEqual(stderr.splitlines(),
            [b"Traceback (most recent call last):",
             b"  File \"<string>\", line 1, in <module>",
             b"DeprecationWarning: Message"])

    def test_default_filter_configuration(self):
        pure_python_api = self.module is py_warnings
        if Py_DEBUG:
            expected_default_filters = []
        else:
            if pure_python_api:
                main_module_filter = re.compile("__main__")
            else:
                main_module_filter = "__main__"
            expected_default_filters = [
                ('default', None, DeprecationWarning, main_module_filter, 0),
                ('ignore', None, DeprecationWarning, None, 0),
                ('ignore', None, PendingDeprecationWarning, None, 0),
                ('ignore', None, ImportWarning, None, 0),
                ('ignore', None, ResourceWarning, None, 0),
            ]
        expected_output = [str(f).encode() for f in expected_default_filters]

        if pure_python_api:
            # Disable the warnings acceleration module in the subprocess
            code = "import sys; sys.modules.pop('warnings', None); sys.modules['_warnings'] = None; "
        else:
            code = ""
        code += "import warnings; [print(f) for f in warnings.filters]"

        rc, stdout, stderr = assert_python_ok("-c", code, __isolated=True)
        stdout_lines = [line.strip() for line in stdout.splitlines()]
        self.maxDiff = None
        self.assertEqual(stdout_lines, expected_output)


class PyEnvironmentVariableTests(EnvironmentVariableTests, unittest.TestCase):
    module = py_warnings


class FinalizationTest(unittest.TestCase):
    @support.requires_type_collecting
    def test_finalization(self):
        # Issue #19421: warnings.warn() should not crash
        # during Python finalization
        code = """
import warnings
warn = warnings.warn

class A:
    def __del__(self):
        warn("test")

A()
import gc; gc.collect()
        """
        rc, out, err = assert_python_ok("-c", code)
        self.assertEqual(err.decode(), '-c:7: UserWarning: test')


def setUpModule():
    py_warnings.onceregistry.clear()
    c_warnings.onceregistry.clear()

tearDownModule = setUpModule

if __name__ == "__main__":
    unittest.main()
