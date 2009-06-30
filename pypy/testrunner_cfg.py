# nightly test configuration for the paraller runner

def collect_one_testdir(testdirs, reldir, tests):
    if (reldir.startswith('translator/c/') or 
        reldir.startswith('rlib/test') or
        reldir.startswith('rpython/memory/') or
        reldir.startswith('jit/backend/x86/') or
        reldir.startswith('jit/backend/minimal/')):
        testdirs.extend(tests)
    else:
        testdirs.append(reldir)

    
