import pytest
from pathlib import Path
from . import support


def expand_template(template, name):
    return support.DefaultExtensionTemplate(template, name).expand()


def test_expand_template():
    expanded = expand_template("""
        @EXPORT(f)
        @EXPORT(g)
        some more C stuff
        @INIT
    """, name='mytest')
    defines_table = ['&f,', '&g,']
    defines = '\n    '.join(defines_table)
    init_code = support.DefaultExtensionTemplate.INIT_TEMPLATE % {
        'defines': defines,
        'legacy_methods': 'NULL',
        'name': 'mytest',
        'init_types': '',
        'globals_defs': '',
        'globals_field': '',
    }
    assert expanded.rstrip() == f"""#include <hpy.h>

some more C stuff
{init_code}
""".rstrip()


TEST_DIR = Path(__file__).parent


def test_source_dump(tmpdir):
    import pytest
    test_file = 'test_00_basic'
    parts = ['TestBasic', 'test_noop_function']
    rc = pytest.main(['--dump-dir=' + str(tmpdir), '::'.join([str(TEST_DIR.joinpath(test_file + ".py"))] + parts)])
    assert rc == 0
    expected_dir = '_'.join([test_file] + parts)
    print("expected_dir = " + expected_dir)
    test_dump_dir = None
    for child in Path(tmpdir).iterdir():
        if expected_dir in str(child):
            test_dump_dir = Path(child)
    assert test_dump_dir and test_dump_dir.exists()
    assert test_dump_dir.joinpath('mytest.c').exists()
