import pypy.module.unipycation.engine as eng
#from prolog.interpreter.continuation import Engine

class AppTestEngine(object):
    spaceconfig = dict(usemodules=('unipycation',))

    def test_basic(self):
        import unipycation

        e = unipycation.Engine("likes(mac, jazz). likes(bob, jazz). likes(jim, funk).")
        assert isinstance(e, unipycation.Engine)

        e.query("likes(X, jazz).")

        e.print_last_result()
