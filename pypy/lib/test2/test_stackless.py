from pypy.conftest import gettestobjspace
 
class AppTest_Stackless(object):

    def setup_class(cls):
        cls.space = gettestobjspace('std', usemodules=("_stackless",))


    def test_simple_pipe(self):
        
        from stackless import run, tasklet, channel

        def pipe(X_in, X_out):
            foo = X_in.receive()
            X_out.send(foo)

        X, Y = channel(), channel()
        tasklet(pipe)(X, Y)
        run()
        X.send(42)
        assert Y.receive() == 42

    def test_nested_pipe(self):
        from stackless import run, tasklet, channel
        run()

        def pipe(X, Y):
            foo = X.receive()
            Y.send(foo)

        def nest(X, Y):
            X2, Y2 = channel(), channel()
            tasklet(pipe)(X2, Y2)
            X2.send(X.receive())
            Y.send(Y2.receive())

        X, Y = channel(), channel()
        tasklet(nest)(X, Y)
        X.send(42)
        assert Y.receive() == 42
        

    def test_wait_two(self):
        """
        A tasklets/channels adaptation of the test_wait_two from the
        logic object space
        """
        from stackless import run, tasklet, channel
        run()
        
        def sleep(X, Barrier):
            Barrier.send((X, X.receive()))

        def wait_two(X, Y, Ret_chan):
            Barrier = channel()
            tasklet(sleep)(X, Barrier)
            tasklet(sleep)(Y, Barrier)
            ret = Barrier.receive()
            if ret[0] == X:
                Ret_chan.send((1, ret[1]))
            return Ret_chan.send((2, ret[1]))

        X, Y, Ret_chan = channel(), channel(), channel()
        tasklet(wait_two)(X, Y, Ret_chan)
        Y.send(42)
        X.send(42)
        assert Ret_chan.receive() == (2, 42)
