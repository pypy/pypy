

class AppTestAtomic:
    spaceconfig = dict(usemodules=['pypystm', 'thread'])

    def test_simple(self):
        import pypystm
        for atomic in (pypystm.atomic, pypystm.exclusive_atomic,
                       pypystm.single_transaction):
            with atomic:
                assert pypystm.is_atomic()
            try:
                with atomic:
                    raise ValueError
            except ValueError:
                pass

    def test_nest_composable_atomic(self):
        import pypystm
        with pypystm.atomic:
            with pypystm.atomic:
                assert pypystm.is_atomic()
            assert pypystm.is_atomic()
        assert not pypystm.is_atomic()

    def test_nest_composable_below_exclusive(self):
        import pypystm
        with pypystm.exclusive_atomic:
            with pypystm.atomic:
                with pypystm.atomic:
                    assert pypystm.is_atomic()
                assert pypystm.is_atomic()
            assert pypystm.is_atomic()
        assert not pypystm.is_atomic()

    def test_nest_exclusive_fails(self):
        import pypystm
        try:
            with pypystm.exclusive_atomic:
                with pypystm.exclusive_atomic:
                    assert pypystm.is_atomic()
        except pypystm.error, e:
            assert not pypystm.is_atomic()
            assert e.message == "exclusive_atomic block can't be entered inside another atomic block"

    def test_nest_exclusive_fails2(self):
        import pypystm
        try:
            with pypystm.atomic:
                with pypystm.exclusive_atomic:
                    assert pypystm.is_atomic()
                assert pypystm.is_atomic()
        except pypystm.error, e:
            assert not pypystm.is_atomic()
            assert e.message == "exclusive_atomic block can't be entered inside another atomic block"
