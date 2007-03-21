import inspect
import os
from cclp import switch_debug_info

def raises(exception, call, *args):
    try:
        call(*args)
    except exception:
        return True
    except:
        pass
    return False

class Skip(Exception): pass

def skip(desc):
    raise Skip, desc

def out(obj):
    os.write(1, str(obj))

def get_test_classes():
    return [obj for name, obj in inspect.getmembers(tm)
            if isinstance(obj, type)]

def get_test_methods(klass):
    return [(name, meth)
            for name, meth in inspect.getmembers(klass())
            if not name.startswith('_')]

def run_tests(tm, selected_tests):
    
    tm.raises = raises
    tm.skip = skip
    
    successes = []
    failures = []
    skipped = []
    all_tests = [get_test_methods(cl) for cl in get_test_classes()]
    print "testing %s test(s) classe(s)" % len(all_tests)
    for tests in all_tests:
        for name, meth in tests:
            if name == 'setup_class': continue
            if selected_tests and name not in selected_tests:
                continue
            try:
                meth()
            except Skip, s:
                skipped.append((name, s.args[0]))
                out('s')
            except Exception, e:
                failures.append((name, meth, e))
                out('F')
            else:
                successes.append(name)
                out('.')
    out('\n')

    if successes:
        print "Successes :"
        print '', '\n '.join(successes)
        print
    if failures:
        print "Failures :"
        for name, _, exc in failures:
            print '', name, "failed because", str(exc)
        print
    if skipped:
        print "Skipped"
        for name, cause in skipped:
            print '', name, "skipped because", cause
        print

    # replay failures with more info
    switch_debug_info()
    for name, meth, _ in failures:
        meth()
        
if __name__ == __name__:
    import sys
    tm = __import__(sys.argv[1])
    tests = []
    try:
        tests += (sys.argv[2:])
    except:
        pass
    run_tests(tm, tests)
