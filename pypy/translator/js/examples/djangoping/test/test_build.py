
from pypy.translator.js.main import rpython2javascript

def test_build():
    from pypy.translator.js.examples.djangoping import client
    assert rpython2javascript(client, ['ping_init'], use_pdb=False)
