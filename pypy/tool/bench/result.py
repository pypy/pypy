
class PerfResult:
    """Holds information about a benchmark run of a particular test run."""
    
    def __init__(self, date=0.0, test_id="", revision=0.0, 
                 revision_id="NONE", timestamp=0.0,
                 revision_date=0.0, elapsed_time=-1, 
                 committer="", message="", nick=""): 
        self.__dict__.update(locals())
        del self.self

        
class PerfResultCollection(object):
    """Holds informations about several PerfResult objects. The
    objects should have the same test_id and revision_id"""
    
    def __init__(self, results=None):
        if results is None:
            self.results = []
        else:
            self.results = results[:]
        #self.check()

    def __repr__(self):
        self.check()
        if not self.results:
            return "<PerfResultCollection EMPTY>"
        sample = self.results[0]
        return "<PerfResultCollection test_id=%s, revno=%s>" %(
               sample.test_id, sample.revision)
    
    @property   
    def min_elapsed(self):
        return self.getfastest().elapsed_time 

    def getfastest(self):
        x = None
        for res in self.results:
            if x is None or res.elapsed_time < x.elapsed_time: 
                x = res
        return x

    @property
    def test_id(self):
        # check for empty results?
        return self.results[0].test_id

    @property
    def revision_id(self):
        # check for empty results?
        return self.results[0].revision_id

    @property
    def revision(self):
        # check for empty results?
        return self.results[0].revision
           
    def check(self):
        for s1, s2 in zip(self.results, self.results[1:]):
            assert s1.revision_id == s2.revision_id 
            assert s1.test_id == s2.test_id
            assert s1.revision == s2.revision
            assert s1.date != s2.date
            
    def append(self, sample):
        self.results.append(sample)
        self.check()

    def extend(self, results):
        self.results.extend(results)
        self.check() 
        
    def __len__(self):
        return len(self.results)


class PerfResultDelta:
    """represents the difference of two PerfResultCollections"""

    def __init__(self, _from, _to=None): 
        if _from is None:
            _from = _to
        if _to is None:
            _to = _from
        if isinstance(_from, list):
            _from = PerfResultCollection(_from)
        if isinstance(_to, list):
            _to = PerfResultCollection(_to)
        assert isinstance(_from, PerfResultCollection)
        assert isinstance(_to, PerfResultCollection)
        assert _from.test_id == _to.test_id, (_from.test_id, _to.test_id)
        self._from = _from
        self._to = _to
        self.test_id = self._to.test_id
        self.delta = self._to.min_elapsed - self._from.min_elapsed 

        # percentage
        m1 = self._from.min_elapsed 
        m2 = self._to.min_elapsed 
        if m1 == 0: 
            self.percent = 0.0
        else:
            self.percent = float(m2-m1) / float(m1)

