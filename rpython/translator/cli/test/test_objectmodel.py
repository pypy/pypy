import py
from rpython.translator.cli.test.runtest import CliTest
from rpython.translator.oosupport.test_template.objectmodel import \
     BaseTestObjectModel

def skip_r_dict(self):
    py.test.skip('r_dict support is still incomplete')

class TestCliObjectModel(CliTest, BaseTestObjectModel):
    test_rtype_r_dict_bm = skip_r_dict
