import py

from pypy.translator.driver import TranslationDriver
from py.compat import optparse

def test_ctr():
    td = TranslationDriver()
    expected = ['annotate', 'backendopt', 'llinterpret', 'rtype', 'source',
                'compile', 'run', 'prehannotatebackendopt', 'hintannotate',
                'timeshift']
    assert set(td.exposed) == set(expected)

    assert td.backend_select_goals(['compile_c']) == ['compile_c']
    assert td.backend_select_goals(['compile']) == ['compile_c']
    assert td.backend_select_goals(['rtype']) == ['rtype_lltype']
    assert td.backend_select_goals(['rtype_lltype']) == ['rtype_lltype']
    assert td.backend_select_goals(['backendopt']) == ['backendopt_lltype']
    assert td.backend_select_goals(['backendopt_lltype']) == [
        'backendopt_lltype']

    td = TranslationDriver({'backend': None, 'type_system': None})

    assert td.backend_select_goals(['compile_c']) == ['compile_c']
    py.test.raises(Exception, td.backend_select_goals, ['compile'])
    py.test.raises(Exception, td.backend_select_goals, ['rtype'])
    assert td.backend_select_goals(['rtype_lltype']) == ['rtype_lltype']
    py.test.raises(Exception, td.backend_select_goals, ['backendopt'])
    assert td.backend_select_goals(['backendopt_lltype']) == [
        'backendopt_lltype']

    expected = ['annotate', 'backendopt_lltype',
                 'backendopt_ootype',
                 'llinterpret_lltype',
                 'rtype_ootype', 'rtype_lltype', 'source_js',
                 'source_cli', 'source_c', 'source_llvm',
                 'compile_cli', 'compile_c',
                 'compile_llvm', 'compile_js',
                 'run_llvm', 'run_c', 'run_js', 'run_cli',
                 'compile_jvm', 'source_jvm', 'run_jvm',
                 'prehannotatebackendopt_lltype', 'hintannotate_lltype',
                 'timeshift_lltype']
    assert set(td.exposed) == set(expected)                             

    td = TranslationDriver({'backend': None, 'type_system': 'lltype'})

    assert td.backend_select_goals(['compile_c']) == ['compile_c']
    py.test.raises(Exception, td.backend_select_goals, ['compile'])
    assert td.backend_select_goals(['rtype_lltype']) == ['rtype_lltype']
    assert td.backend_select_goals(['rtype']) == ['rtype_lltype']
    assert td.backend_select_goals(['backendopt']) == ['backendopt_lltype']
    assert td.backend_select_goals(['backendopt_lltype']) == [
        'backendopt_lltype']

    expected = ['annotate', 'backendopt', 'llinterpret', 'rtype', 'source_c',
                'source_llvm', 'compile_c', 'compile_llvm', 'run_llvm',
                'run_c', 'prehannotatebackendopt', 'hintannotate', 'timeshift']

    assert set(td.exposed) == set(expected)
