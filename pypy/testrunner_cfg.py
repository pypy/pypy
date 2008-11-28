# nightly test configuration for the paraller runner

def collect_one_testdir(testdirs, reldir, tests):
    if (reldir.startswith('jit/codegen/i386/') or
        reldir.startswith('jit/timeshifter/') or
        reldir.startswith('translator/c/') or 
        reldir.startswith('rlib/test') or
        reldir.startswith('rpython/memory/')):
        testdirs.extend(tests)
    else:     
        testdirs.append(reldir)

    
