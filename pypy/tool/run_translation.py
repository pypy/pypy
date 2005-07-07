import os
import sys
from py.path import svnwc

transl_test = """
import sys
module = __import__('pypy.translator.goal.%s', None, None, ['target'])
entry_point, arg_s = module.target()

from pypy.translator.translator import Translator
from pypy.translator.goal.query import polluted

t = Translator(entry_point)
a = t.annotate(arg_s)
a.simplify()

print polluted(t)
"""

def prepare(repository, wcdir, revision):
    """
    Checks out the named revision into wcdir and returns an object
    with metadata that can be fed to execute and cleanup.
    """
    class ExecutionData:
        def __init__(self, wcdir):
            self.wcdir = wcdir

    # Make sure the base dir exists
    if os.path.exists(wcdir):
        raise RuntimeError("working directory already exists")

    # Checkout revision
    wc = svnwc(wcdir)
    wc.checkout(repository, rev=revision)
    return ExecutionData(wcdir)

def execute(goal, execdata):
    """
    Tests annotation of supplied goal. Goal should be a string with an
    importable name from pypy.translator.goal.
    """
    if not os.path.exists(execdata.wcdir):
        raise RuntimeError("Run prepare to get a working directory")
    # Make sure imports are from checked out source
    test_file_name = os.tmpnam()
    test_file = open(test_file_name, "w")
    test_file.write(transl_test % (goal,))
    test_file.close()
    os.system("PYTHONPATH=%s python %s" % (execdata.wcdir, test_file_name))
    os.remove(test_file_name)

def cleanup(execdata):
    """
    Removes working directory named by execdata.
    """
    for root, dirs, files in os.walk(execdata.wcdir, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(execdata.wcdir)
