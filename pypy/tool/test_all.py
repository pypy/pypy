#!/usr/bin/python

import sys,os,glob,inspect, unittest
from os.path import join as joinfn
from os.path import basename, dirname, abspath
sepline = '='*70


def eval_dict_from(fn):
    os.chdir(dirname(fn))
    d = {}
    try:
        execfile(fn, d)
    except IOError:
        pass 
    return d

class exec_testfile:
    def __init__(self, modfn, testfn):
        self.testdict = eval_dict_from(testfn)
        self.moddict = eval_dict_from(modfn)

        for name, obj in self.testdict.items():
            if inspect.isclass(obj) and issubclass(obj, unittest.TestCase) and \
               name.startswith('Test'):
                self.exec_testclass(name, obj)

    def exec_testclass(self, name, obj):
        if name[4:] not in self.moddict.keys():
            print repr(name), "does not correspond to a class"
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(obj, 'test'))
        print "running unittest", name
        unittest.TextTestRunner().run(suite)
        print "finished"


def filetests(path):
    """tests files on the given path"""
    testpath = joinfn(path, 'test')
    testfnames = glob.glob(testpath+os.sep+'test_*.py')
    fnames = glob.glob(path+os.sep+'*.py')
    
    for testfn in testfnames:
        print sepline
        modfn = joinfn(path, basename(testfn)[5:])

        if modfn not in fnames:
            print "testfile", basename(testfn), "has no", basename(modfn)
        else:
            fnames.remove(modfn)
        exec_testfile(modfn, testfn)
    #for fn in fnames:
    #    print fn, "has no corresponding test?"
        
def drive_tests(base):
    ctests = filetests(joinfn(base, 'interpreter'))

if __name__=='__main__':
    path = dirname(abspath(sys.argv[0]))
    drive, path = os.path.splitdrive(path)
    path = path.split(os.sep)
    
    if 'pypy' not in path:
        raise SystemExit, "Need to be somewhere in pypy-tree"
    
    while path.pop() != 'pypy': 
        pass
    
    path.insert(0, '/')
    path.append('pypy')
    path = drive + joinfn('/', *path)
    print path, dirname(path)
    sys.path.insert(0, dirname(path))
    drive_tests(path)
