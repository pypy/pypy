# nightly test configuration for the paraller runner

def collect_one_testdir(testdirs, reldir, tests):
    if (reldir.startswith('jit/codegen/i386/') or
        reldir.startswith('jit/timeshifter/') or
        reldir.startswith('translator/c/')):
        testdirs.extend(tests)
    else:     
        testdirs.append(reldir)

    
