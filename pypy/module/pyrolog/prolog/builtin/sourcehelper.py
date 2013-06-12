import os
import sys
from prolog.interpreter.error import throw_existence_error
from prolog.interpreter.term import Callable

path = os.path.dirname(__file__)
path = os.path.join(path, "..", "prolog_modules")

def get_source(filename):
    try:
        assert isinstance(filename, str)
        fd = get_filehandle(filename, True)
    except OSError:
        throw_existence_error("source_sink", Callable.build(filename))
        assert 0, "unreachable" # make the flow space happy
    try:
        content = []
        while 1:
            s = os.read(fd, 4096)
            if not s:
                break
            content.append(s)
        file_content = "".join(content)
    finally:
        os.close(fd)
    return file_content

def get_filehandle(filename, stdlib=False):
    assert isinstance(filename, str)
    try:
        return os.open(filename, os.O_RDONLY, 0777)
    except OSError, e:
        try:
            temppath = filename + ".pl"
            assert isinstance(temppath, str)
            return os.open(temppath, os.O_RDONLY, 0777)
        except OSError, e:
            if stdlib:
                try:
                    fname = os.path.join(path, filename)
                    assert isinstance(fname, str)
                    return os.open(fname, os.O_RDONLY, 0777)
                except OSError, e:
                    assert isinstance(temppath, str)
                    fname = os.path.join(path, temppath)
                    assert isinstance(fname, str)
                    return os.open(fname, os.O_RDONLY, 0777)
            raise e
            assert 0, "unreachable"
