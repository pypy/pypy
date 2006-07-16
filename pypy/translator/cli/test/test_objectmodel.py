import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_objectmodel import BaseTestObjectModel

def skip_r_dict(self):
    py.test.skip('r_dict support is still incomplete')

class TestCliObjectModel(CliTest, BaseTestObjectModel):
    test_rtype_r_dict_bm = skip_r_dict
    test_rtype_constant_r_dicts = skip_r_dict
    test_rtype_r_dict_singlefrozen_func = skip_r_dict

    def test_hint(self):
        py.test.skip('Hint is not supported, yet')
    
