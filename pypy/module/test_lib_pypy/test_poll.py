class AppTestPoll:

    spaceconfig = dict(usemodules=('select',))

    def test_poll3(self):
        import select
        # test int overflow
        pollster = select.poll()
        pollster.register(1)

        raises(OverflowError, pollster.register, 0, -1)
        raises(OverflowError, pollster.register, 0, 1 << 64)
        raises(OverflowError, pollster.modify, 1, -1)
        raises(OverflowError, pollster.modify, 1, 1 << 64)
