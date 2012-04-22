import os
from pypy.tool.udir import udir


def test_all():
    executable = str(udir.join('test_stmgcintf'))
    exitcode = os.system("gcc -g -o '%s' -pthread -I.. test_stmgcintf.c" % (
        executable,))
    assert exitcode == 0
    #
    for line in open('test_stmgcintf.c'):
        line = line.strip()
        if line.startswith('XTEST('):
            assert line.endswith(');')
            yield run_one_test, executable, line[6:-2]


def run_one_test(executable, testname):
    exitcode = os.system("'%s' %s" % (executable, testname))
    assert exitcode == 0, "exitcode is %r running %r" % (exitcode, testname)
