import py
from prolog.builtin.sourcehelper import get_source
from prolog.interpreter.test.tool import collect_all, assert_false, assert_true
from prolog.interpreter.test.tool import prolog_raises, create_file, delete_file
from prolog.interpreter.error import CatchableError

def test_get_source():
    content = "some important content"
    name = "__testfile__"
    try:
        create_file(name, content)
        source = get_source(name)
        assert source == content
    finally:
        delete_file(name)

def test_source_does_not_exist():
    py.test.raises(CatchableError, "get_source('this_file_does_not_exist')")

def test_file_ending():
    content = "some content"
    filename = "__testfile__.pl"
    searchname = filename[:len(filename) - 3]
    try:
        create_file(filename, content)
        source = get_source(searchname)
        assert source == content
    finally:
        delete_file(filename)



