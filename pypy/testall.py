import os
import unittest
import sys

try:
    head = this_path = os.path.abspath(__file__)
except NameError:
    head = this_path = os.path.abspath(os.path.dirname(sys.argv[0]))
while 1:
    head, tail = os.path.split(head)
    if not tail:
        raise EnvironmentError, "pypy not among parents of %r!" % this_path
    elif tail.lower()=='pypy':
        PYPYDIR = head
        if PYPYDIR not in sys.path:
            sys.path.insert(0, PYPYDIR)
        break

def find_tests(root):
    testmods = []
    def callback(arg, dirname, names):
        if os.path.basename(dirname) == 'test':
            package = dirname[len(PYPYDIR)+1:].replace(os.sep, '.')
            testfiles = [f[:-3] for f in names
                         if f.startswith('test_') and f.endswith('.py')]
            for file in testfiles:
                testmods.append(package + '.' + file)
            
    os.path.walk(root, callback, None)
    
    tl = unittest.TestLoader()
    
    return tl.loadTestsFromNames(testmods)

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(find_tests(PYPYDIR))
    
    
