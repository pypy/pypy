import inspect

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
    print "skipping because", desc
    raise Skip

def run_tests(tm):
    classes = [obj for name, obj in inspect.getmembers(tm)
               if isinstance(obj, type)]

    tm.raises = raises
    tm.skip = skip

    successes = []
    failures = []
    skipped = []


    for klass in classes:
        tests = [(name, meth) for name, meth in inspect.getmembers(klass())
                 if not name.startswith('_')]
        for name, meth in tests:
            if name == 'setup_class': continue
            try:
                meth()
            except Skip:
                skipped.append(name)
            except Exception, e:
                failures.append((name, e))
            else:
                successes.append(name)

    if successes:
        print "Successes :"
        print '', '\n '.join(successes)
        print
    if failures:
        print "Failures :"
        for name, exc in failures:
            print '', name, "failed because", str(exc)
        print
    if skipped:
        print "Skipped"
        print '', '\n '.join(skipped)
        
if __name__ == __name__:
    import sys
    tm = __import__(sys.argv[1])
    run_tests(tm)
