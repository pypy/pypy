import py, os
from pypy.tool.runsubprocess import run_subprocess

def test_no_such_command():
    py.test.raises(EnvironmentError, run_subprocess,
                   'this_command_does_not_exist', [])
    py.test.raises(EnvironmentError, run_subprocess,
                   'this_command_does_not_exist', [])

def test_echo():
    if not os.path.exists('/bin/echo'):
        py.test.skip("there is no /bin/echo")
    returncode, stdout, stderr = run_subprocess('/bin/echo', 'FooBar')
    assert returncode == 0
    assert stdout == 'FooBar\n'
    assert stderr == ''

def test_false():
    if not os.path.exists('/bin/false'):
        py.test.skip("there is no /bin/false")
    returncode, stdout, stderr = run_subprocess('/bin/false', [])
    assert returncode == 1
    assert stdout == ''
    assert stderr == ''

def test_cat_fail():
    if not os.path.exists('/bin/cat'):
        py.test.skip("there is no /bin/cat")
    returncode, stdout, stderr = run_subprocess('/bin/cat', 'no/such/filename')
    assert returncode == 1
    assert stdout == ''
    assert 'no/such/filename' in stderr
