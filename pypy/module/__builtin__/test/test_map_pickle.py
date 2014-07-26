class AppTestMapPickle:

    def test_map_pickle(self):
        """Pickle a map with one sequence."""
        import pickle

        def pickle_unpickle(obj):
            d = pickle.dumps(obj)
            return pickle.loads(d)

        m1 = map(ord, "Is this the real life?")
        m1_ = pickle_unpickle(m1)

        assert list(m1) == list(m1_)

    def test_map2_pickle(self):
        """Pickle a map with multiple sequences."""
        import pickle

        def pickle_unpickle(obj):
            d = pickle.dumps(obj)
            return pickle.loads(d)

        m1 = map(max, "abc", "def")
        m1_ = pickle_unpickle(m1)

        assert list(m1) == list(m1_)

