import os
from pypy.tool import autopath
from pypy.tool.udir import udir


def test_all():
    executable = str(udir.join('test_stmgcintf'))
    prevdir = os.getcwd()
    thisdir = os.path.join(autopath.pypydir, 'translator', 'stm', 'test')
    try:
        os.chdir(thisdir)
        exitcode = os.system(
            "gcc -g -o '%s' -pthread -I.. test_stmgcintf.c" % (
            executable,))
        assert exitcode == 0
    finally:
        os.chdir(prevdir)
    #
    for line in open(os.path.join(thisdir, 'test_stmgcintf.c')):
        line = line.strip()
        if line.startswith('XTEST('):
            assert line.endswith(');')
            yield run_one_test, executable, line[6:-2]


def run_one_test(executable, testname):
    exitcode = os.system("'%s' %s" % (executable, testname))
    assert exitcode == 0, "exitcode is %r running %r" % (exitcode, testname)
