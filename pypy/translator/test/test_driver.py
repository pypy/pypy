import py

from pypy.translator.driver import TranslationDriver, DEFAULT_OPTIONS
import optparse

def cmpl(l1, l2):
    l1 = list(l1)
    l2 = list(l2)
    l1.sort()
    l2.sort()
    return l1 == l2

def test_ctr():
    td = TranslationDriver()

    assert cmpl(td.exposed,
                ['annotate', 'backendopt', 'llinterpret', 'rtype', 'source', 'compile', 'run'])

    assert td.backend_select_goals(['compile_c']) == ['compile_c']
    assert td.backend_select_goals(['compile']) == ['compile_c']
    assert td.backend_select_goals(['rtype']) == ['rtype_lltype']
    assert td.backend_select_goals(['rtype_lltype']) == ['rtype_lltype']
    assert td.backend_select_goals(['backendopt']) == ['backendopt_lltype']
    assert td.backend_select_goals(['backendopt_lltype']) == ['backendopt_lltype']          

    d = DEFAULT_OPTIONS.copy()
    d['backend'] = None
    td = TranslationDriver(options=optparse.Values(defaults=d))

    assert td.backend_select_goals(['compile_c']) == ['compile_c']
    py.test.raises(Exception, td.backend_select_goals, ['compile'])
    py.test.raises(Exception, td.backend_select_goals, ['rtype'])
    assert td.backend_select_goals(['rtype_lltype']) == ['rtype_lltype']          
    py.test.raises(Exception, td.backend_select_goals, ['backendopt'])
    assert td.backend_select_goals(['backendopt_lltype']) == ['backendopt_lltype']          


    assert cmpl(td.exposed,
                ['annotate', 'backendopt_lltype', 'llinterpret_lltype',
                 'rtype_ootype', 'rtype_lltype',
                 'source_cl', 'source_js', 'source_squeak', 'source_cli', 'source_c',
                 'source_llvm', 'compile_cl', 'compile_cli', 'compile_c', 'compile_squeak',
                 'compile_llvm', 'compile_js', 'run_cl', 'run_squeak', 'run_llvm',
                 'run_c', 'run_js', 'run_cli'])

    d = DEFAULT_OPTIONS.copy()
    d['backend'] = None
    d['type_system'] = 'lltype'
    td = TranslationDriver(options=optparse.Values(defaults=d))

    assert td.backend_select_goals(['compile_c']) == ['compile_c']
    py.test.raises(Exception, td.backend_select_goals, ['compile'])
    assert td.backend_select_goals(['rtype_lltype']) == ['rtype_lltype']    
    assert td.backend_select_goals(['rtype']) == ['rtype_lltype']    
    assert td.backend_select_goals(['backendopt']) == ['backendopt_lltype']
    assert td.backend_select_goals(['backendopt_lltype']) == ['backendopt_lltype']          

    assert cmpl(td.exposed,
                ['annotate', 'backendopt', 'llinterpret', 'rtype', 'source_c', 'source_llvm',
                 'compile_c', 'compile_llvm', 'run_llvm', 'run_c'])
