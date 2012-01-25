
import py
import sys

innertest = py.path.local(__file__).dirpath('conftest1_innertest.py')
pytest_plugins = "pytester"

class TestPyPyTests:
    def test_selection_by_keyword_interp(self, testdir): 
        sorter = testdir.inline_run("-k", "interplevel", innertest, )
        passed, skipped, failed = sorter.listoutcomes()
        assert len(passed) == 2, len(passed)
        assert not skipped and not failed 
        assert "test_something" in passed[0].nodeid
        assert "test_method" in passed[1].nodeid

    def test_selection_by_keyword_app(self, testdir): 
        sorter = testdir.inline_run("-k", "applevel -docstring", innertest)
        passed, skipped, failed = sorter.listoutcomes()
        assert len(passed) == 2
        assert failed == []
        assert skipped == []
        assert "app_test_something" in passed[0].nodeid
        assert "test_method_app" in passed[1].nodeid

    def test_runappdirect(self, testdir):
        sorter = testdir.inline_run(innertest, '-k', 'applevel -docstring',
                                    '--runappdirect')
        passed, skipped, failed = sorter.listoutcomes()
        assert len(passed) == 2
        print passed
        assert "app_test_something" in passed[0].nodeid
        assert "test_method_app" in passed[1].nodeid
        
    def test_appdirect(self, testdir):
        sorter = testdir.inline_run(innertest, '-k', 'applevel -docstring',
                                    '--appdirect=%s' % (sys.executable,))
        passed, skipped, failed = sorter.listoutcomes()
        assert len(passed) == 2
        print passed
        assert "app_test_something" in passed[0].nodeid
        assert "test_method_app" in passed[1].nodeid
        
    def test_docstring_in_methods(self, testdir): 
        sorter = testdir.inline_run("-k", "AppTestSomething test_code_in_docstring",
                                    innertest)
        passed, skipped, failed = sorter.listoutcomes()
        assert len(passed) == 1
        assert len(failed) == 1
        assert skipped == []
        assert "test_code_in_docstring_ignored" in passed[0].nodeid
        assert "test_code_in_docstring_failing" in failed[0].nodeid

    def test_docstring_in_functions(self, testdir): 
        sorter = testdir.inline_run("-k", "app_test_code_in_docstring", innertest)
        passed, skipped, failed = sorter.listoutcomes()
        assert passed == []
        assert len(failed) == 1
        assert skipped == []
        assert "app_test_code_in_docstring_failing" in failed[0].nodeid

    def test_docstring_runappdirect(self, testdir):
        sorter = testdir.inline_run(innertest,
                                    '-k', 'test_code_in_docstring',
                                    '--runappdirect')
        passed, skipped, failed = sorter.listoutcomes()
        assert len(passed) == 1
        assert len(skipped) == 2
        assert "test_code_in_docstring_ignored" in passed[0].nodeid
        assert "app_test_code_in_docstring_failing" in skipped[0].nodeid
        assert "test_code_in_docstring_failing" in skipped[1].nodeid

    def test_docstring_appdirect(self, testdir):
        sorter = testdir.inline_run(innertest,
                                    '-k', 'test_code_in_docstring',
                                    '--appdirect=%s' % (sys.executable,))
        passed, skipped, failed = sorter.listoutcomes()
        assert len(passed) == 1
        assert len(failed) == 2
        assert "test_code_in_docstring_ignored" in passed[0].nodeid
        assert "app_test_code_in_docstring_failing" in failed[0].nodeid
        assert "test_code_in_docstring_failing" in failed[1].nodeid
