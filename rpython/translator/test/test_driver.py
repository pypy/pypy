import py

from rpython.translator.driver import TranslationDriver

def test_ctr():
    td = TranslationDriver()
    expected = ['annotate', 'backendopt', 'llinterpret', 'rtype', 'source',
                'compile', 'pyjitpl']
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

    expected = ['annotate', 'backendopt_lltype', 'llinterpret_lltype',
                'rtype_lltype', 'source_c', 'compile_c', 'pyjitpl_lltype', ]
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
                'compile_c', 'pyjitpl']

    assert set(td.exposed) == set(expected)
