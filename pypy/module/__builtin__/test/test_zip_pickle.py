class AppTestZipPickle:

    def test_zip_pickle(self):
        import pickle

        def pickle_unpickle(obj):
            d = pickle.dumps(obj)
            return pickle.loads(d)

        z1 = zip([1, 2, 3], [4, 5, 6])
        z1_ = pickle_unpickle(z1)
        l1, l1_ = list(z1), list(z1_)

        assert l1 == l1_
