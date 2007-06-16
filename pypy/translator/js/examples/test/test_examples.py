
""" Various build tests
"""
import py
from pypy.translator.js.main import rpython2javascript

def test_console_build():
    from pypy.translator.js.examples import pythonconsole
    httpd = pythonconsole.Server(('', 0), pythonconsole.RequestHandler)
    pythonconsole.httpd = httpd
    # XXX obscure hack
    assert rpython2javascript(pythonconsole, ['setup_page'], use_pdb=False)

def test_bnb_build():
    from pypy.translator.js.examples.bnb import start_bnb
    assert rpython2javascript(start_bnb, ['bnb'], use_pdb=False)

def test_overmind_build():
    from pypy.translator.js.examples import overmind, over_client
    assert rpython2javascript(over_client, overmind.FUNCTION_LIST,
                              use_pdb=False)

def test_guestbook_build():
    from pypy.translator.js.examples import guestbook, guestbook_client
    assert rpython2javascript(guestbook_client, guestbook.FUNCTION_LIST,
                              use_pdb=False)

    
def test_console_2_build():
    from pypy.translator.js.examples.console import console, client
    assert rpython2javascript(client, console.FUNCTION_LIST,
                              use_pdb=True)

def test_ping_play1():
    from urllib import URLopener
    u = URLopener()
    text = "<title>pypy.js various demos</title>"
    assert u.open("http://play1.pypy.org/").read().find(text) != -1
