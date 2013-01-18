import py
import rpython

pytest_plugins = "pytest_pytester"

conftestpath = py.path.local(rpython.__file__).dirpath("conftest.py")


def test_expectcollect(testdir):
    py.test.importorskip("pexpect")
    conftestpath.copy(testdir.tmpdir)
    sorter = testdir.inline_runsource("""
        class ExpectTestOne:
            def test_one(self):
                pass
    """)
    passed, skipped, failed = sorter.countoutcomes()
    assert passed == 1


def test_safename():
    from rpython.tool.pytest.expecttest import ExpectTestMethod

    safe_name = ExpectTestMethod.safe_name
    assert safe_name(['pypy', 'tool', 'test', 'test_pytestsupport.py',
                      'ExpectTest', '()', 'test_one']) == \
           'pypy_tool_test_test_pytestsupport_ExpectTest_paren_test_one'


def test_safe_filename(testdir):
    py.test.importorskip("pexpect")
    conftestpath.copy(testdir.tmpdir)
    sorter = testdir.inline_runsource("""
        class ExpectTestOne:
            def test_one(self):
                pass
    """)
    evlist = sorter.getcalls("pytest_runtest_makereport")
    ev = [x for x in evlist if x.call.when == "call"][0]
    print ev
    sfn = ev.item.safe_filename()
    print sfn
    assert sfn == 'test_safe_filename_test_safe_filename_ExpectTestOne_paren_test_one_1.py'


class ExpectTest:
    def test_one(self):
        import os
        import sys
        assert os.ttyname(sys.stdin.fileno())

    def test_two(self):
        import pypy
