import pytest
from collections import namedtuple

def test_replace_positional_args():
    nt = namedtuple('T', 'a b')
    x = nt(1, 2)
    with pytest.raises(TypeError):
        x._replace(1)

def test_empty_replace():
    nt = namedtuple('empty', '')
    nt()._replace() # does not crash


