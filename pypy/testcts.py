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

def find_tests(root, inc_names=[], exc_names=[]):
    testmods = []
    def callback(arg, dirname, names):
        if os.path.basename(dirname) == 'test':
            parname = os.path.basename(os.path.dirname(dirname))
            if ((not inc_names) or parname in inc_names) and parname not in exc_names:
                package = dirname[len(PYPYDIR)+1:].replace(os.sep, '.')
                testfiles = [f[:-3] for f in names
                             if f.startswith('test_') and f.endswith('.py')]
                for file in testfiles:
                    testmods.append(package + '.' + file)
            
    os.path.walk(root, callback, None)
    
    tl = unittest.TestLoader()
    
    return tl.loadTestsFromNames(testmods)

class MyTestResult(unittest.TestResult):
    def __init__(self):
        unittest.TestResult.__init__(self)
        self.successes = []
    def addSuccess(self, test):
        self.successes.append(test)


class CtsTestRunner:
    def run(self, test):
        import pickle
        
        result = MyTestResult()
        sys.stdout = open('/dev/null', 'w')
        sys.stderr = open('/dev/null', 'w')
        test(result)
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        ostatus = {}
        if os.path.exists('testcts.pickle'):
            ostatus = pickle.load(open('testcts.pickle','r'))

        status = {}

        for e in result.errors:
            name = e[0].__class__.__name__ + '.' + e[0]._TestCase__testMethodName
            status[name] = 'ERROR'
        for f in result.failures:
            name = f[0].__class__.__name__ + '.' + f[0]._TestCase__testMethodName
            status[name] = 'FAILURE'
        for s in result.successes:
            name = s.__class__.__name__ + '.' + s._TestCase__testMethodName
            status[name] = 'success'

        keys = status.keys()
        keys.sort()

        for k in keys:
            old = ostatus.get(k, 'success')
            if k in ostatus:
                del ostatus[k]
            new = status[k]
            if old != new:
                print k, 'has transitioned from', old, 'to', new
            elif new != 'success':
                print k, "is still a", new

        for k in ostatus:
            print k, 'was a', ostatus[k], 'was not run this time'
            status[k] = ostatus[k]

        pickle.dump(status, open('testcts.pickle','w'))
        
        return result

def main(argv=None):
    if argv is None:
        argv = sys.argv

    inc_names = []
    exc_names = []

    os.environ['OBJSPACE'] = 'pypy.objspace.std.objspace.StdObjSpace'

    for arg in argv[1:]:
        if arg.startswith('--include='):
            inc_names = arg[len('--include='):].split(',')
        elif arg.startswith('--exclude='):
            exc_names = arg[len('--exclude='):].split(',')
        else:
            raise Exception, "don't know arg " + arg

    runner = CtsTestRunner()
    runner.run(find_tests(PYPYDIR, inc_names,  exc_names))
    
    
if __name__ == '__main__':
    main()
