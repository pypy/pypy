import py



class AppTestIdentitySet(object):
    
    #needed for compares_by_identity
    spaceconfig = {"objspace.std.withidentitydict": True}
    
    def setup_class(cls):
        from pypy.objspace.std import identitydict
        if cls.runappdirect:
            py.test.skip("interp2app doesn't work on appdirect")
    
    def w_uses_strategy(self, s , obj):
        import __pypy__
        return s in __pypy__.internal_repr(obj)
    
    def test_use_identity_strategy(self):
        
        class Plain(object):
            pass

        class CustomEq(object):
            def __eq__(self, other):
                return True

        class CustomCmp (object):
            def __cmp__(self, other):
                return 0

        class CustomHash(object):
            def __hash__(self):
                return 0
            
        s = set()
        
        assert not self.uses_strategy('IdentitySetStrategy',s)
        
        s.add(Plain())
        
        assert self.uses_strategy('IdentitySetStrategy',s)
        
        for cls in [CustomEq,CustomCmp,CustomHash]:
            s = set()
            s.add(cls())
            assert not self.uses_strategy('IdentitySetStrategy',s)
        
        
    def test_use_identity_strategy_list(self):
        
        class X(object):
            pass
        
        assert self.uses_strategy('IdentitySetStrategy',set([X(),X()]))
        assert not self.uses_strategy('IdentitySetStrategy',set([X(),""]))
        assert not self.uses_strategy('IdentitySetStrategy',set([X(),u""]))
        assert not self.uses_strategy('IdentitySetStrategy',set([X(),1]))
        
    def test_identity_strategy_add(self):
        
        class X(object):
            pass
        
        class NotIdent(object):
            def __eq__(self,other):
                pass
        
        s = set([X(),X()])
        s.add('foo')
        assert not self.uses_strategy('IdentitySetStrategy',s)
        s = set([X(),X()])
        s.add(NotIdent())
        assert not self.uses_strategy('IdentitySetStrategy',s)
    
    def test_identity_strategy_sanity(self):
        
        class X(object):
            pass
        
        class Y(object):
            pass
        
        a,b,c,d,e,f = X(),Y(),X(),Y(),X(),Y()
        
        s = set([a,b]).union(set([c]))
        assert self.uses_strategy('IdentitySetStrategy',s) 
        assert set([a,b,c]) == s
        s = set([a,b,c,d,e,f]) - set([d,e,f])
        assert self.uses_strategy('IdentitySetStrategy',s)
        assert set([a,b,c]) == s
        
        
        s = set([a])
        s.update([b,c])
        
        assert s == set([a,b,c])

