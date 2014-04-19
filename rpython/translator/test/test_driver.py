import py
import os
from rpython.translator.driver import TranslationDriver, shutil_copy
from rpython.tool.udir import udir 

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


def test_create_exe():
    if not os.name == 'nt':
        py.test.skip('Windows only test')

    dst_name = udir.join('dst/pypy.exe')
    src_name = udir.join('src/dydy2.exe')
    dll_name = udir.join('src/pypy.dll')
    lib_name = udir.join('src/pypy.lib')
    src_name.ensure()
    src_name.write('exe')
    dll_name.ensure()
    dll_name.write('dll')
    lib_name.ensure()
    lib_name.write('lib')
    dst_name.ensure()

    class CBuilder(object):
        shared_library_name = dll_name 

    td = TranslationDriver(exe_name=str(dst_name))
    td.c_entryp = str(src_name)
    td.cbuilder = CBuilder()
    td.create_exe()
    assert dst_name.read() == 'exe'
    assert dst_name.new(ext='dll').read() == 'dll'
    assert dst_name.new(purebasename='python27',ext='lib').read() == 'lib'

def test_shutil_copy():
    a = udir.join('file_a')
    b = udir.join('file_a')
    a.write('hello')
    shutil_copy(str(a), str(b))
    assert b.read() == 'hello'
