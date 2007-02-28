class TestBTree(object):

    def test_everything_at_once(self):
        from pypy.objspace.constraint.btree import BTree
        b = BTree()
        l = [(-1, 'egg'), (-7, 'spam'), (3, 'bacon'),
             (99, 'ham'), (77, 'cheese'), (7, 'tomato'),
             (5, 'chicken'), (9, 'noodles')]
        for k, v in l: b.add(k, v)
        assert 77 in b
        assert 66 not in b
        assert b.values() == ['spam', 'egg', 'bacon', 'chicken',
                               'tomato', 'noodles', 'cheese', 'ham']
        assert b.keys() == [-7, -1, 3, 5, 7, 9, 77, 99]
        assert b.items() == [(-7, 'spam'), (-1, 'egg'), (3, 'bacon'),
                             (5, 'chicken'), (7, 'tomato'), (9, 'noodles'),
                             (77, 'cheese'), (99, 'ham')]
