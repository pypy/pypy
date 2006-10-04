import test_logicobjspace as tlo
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

tlo.raises = raises
tlo.skip = skip


classes = [tlo.AppTest_Logic,
           tlo.AppTest_LogicFutures,
           tlo.AppTest_CompSpace]


def run_tests():
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

    if len(successes):
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
        
if __name__ == '__main__':
    run_tests()
