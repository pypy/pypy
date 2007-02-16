"""Tools to work with finite interval domain interval and constraints
"""

from propagation import AbstractDomain, BasicConstraint, \
     ConsistencyFailure, AbstractConstraint

from distributors import AbstractDistributor

class Interval:
    """representation of an interval
    This class is used to give back results from a FiniteIntervalDomain
    """
    def __init__(self, start, end):
        self._start = start
        self._end = end

    def __repr__(self):
        return "<Interval [%.2f %.2f[>" % (self._start, self._end)

    def __eq__(self, other):
        return self._start == other._start and \
               self._end == other._end

class FiniteIntervalDomain(AbstractDomain):
    """
    Domain for a variable with interval values. 
    """
    
    def __init__(self, lowestMin, highestMax,
                 min_length, max_length=None, resolution=1):
        """
        lowestMin is the lowest value of a low boundary for a variable (inclusive).
        highestMax is the highest value of a high boundary for a variable (exclusive).
        min_length is the minimum width of the interval.
        max_length is the maximum width of the interval.
                   Use None to have max = min.
        resolution is the precision to use for constraint satisfaction. Defaults to 1
        """
        assert highestMax >= lowestMin
        if max_length is None:
            max_length = min_length
        assert 0 <= min_length <= max_length
        assert min_length <= highestMax - lowestMin
        assert resolution > 0
        AbstractDomain.__init__(self)
        self.lowestMin = lowestMin
        self.highestMax = highestMax
        self._min_length = min_length
        max_length = min(max_length, highestMax - lowestMin)
        self._max_length = max_length
        self._resolution = resolution

    def __eq__(self, other):
        
        return  self.lowestMin == other.lowestMin and \
               self.highestMax == other.highestMax and \
               self._min_length == other._min_length and \
               self._max_length == other._max_length and \
               self._resolution == other._resolution

    def getValues(self):
        return list(self.iter_values())

    def iter_values(self):
        length = self._min_length
        while length <= self._max_length:
            start = self.lowestMin
            while start + length <= self.highestMax:
                yield Interval(start, start+length)
                start += self._resolution
            length += self._resolution
        
        
    def size(self):
        """computes the size of a finite interval"""
        size = 0
        length = self._min_length 
        while length <= self._max_length :
            size += ((self.highestMax - length) - self.lowestMin) / self._resolution + 1
            length += self._resolution
        return size

    def _highestMin(self):
        return self.highestMax - self._min_length

    def _lowestMax(self):
        return self.lowestMin + self._min_length

    lowestMax = property(_lowestMax, None, None, "")
    
    highestMin = property(_highestMin, None, None, "")

    def copy(self):
        """clone the domain"""
        return FiniteIntervalDomain(self.lowestMin, self.highestMax,
                                    self._min_length, self._max_length,
                                    self._resolution)

    def setLowestMin(self, new_lowestMin):
        self.lowestMin = new_lowestMin
        self._valueRemoved()

    def setHighestMax(self, new_highestMax):
        self.highestMax = new_highestMax
        self._valueRemoved()

    def setMinLength(self, new_min):
        self._min_length = new_min
        self._valueRemoved()

    def setMaxLength(self, new_max):
        self._max_length = new_max
        self._valueRemoved()

    def overlap(self, other):
        return other.highestMax > self.lowestMin and \
               other.lowestMin < self.highestMax

    def no_overlap_impossible(self, other):
        return self.lowestMax > other.highestMin and \
               other.lowestMax > self.highestMin

    def hasSingleLength(self):
        return self._max_length == self._min_length

    def _valueRemoved(self):
        if self.lowestMin >= self.highestMax:
            raise ConsistencyFailure("earliest start [%.2f] higher than latest end  [%.2f]" %
                                     (self.lowestMin, self.highestMax))
        if self._min_length > self._max_length:
            raise ConsistencyFailure("min length [%.2f] greater than max length [%.2f]" %
                                     (self._min_length, self._max_length))

        self._max_length = min(self._max_length, self.highestMax - self.lowestMin)

        if self.size() == 0:
            raise ConsistencyFailure('size is 0')
        
                                 
    
    def __repr__(self):
        return '<FiniteIntervalDomain from [%.2f, %.2f[ to [%.2f, %.2f[>' % (self.lowestMin,
                                                                             self.lowestMax,
                                                                             self.highestMin,
                                                                             self.highestMax)

##
## Distributors
##    

class FiniteIntervalDistributor(AbstractDistributor):
    """Distributes a set of FiniteIntervalDomain
    The distribution strategy is the following:
     - the smallest domain of size > 1 is picked
     - if its max_length is greater than its min_length, a subdomain if size
       min_length is distributed, with the same boundaries
     - otherwise, a subdomain [lowestMin, lowestMax[ is distributed
    """
    def __init__(self):
        AbstractDistributor.__init__(self)

    def _split_values(self, copy1, copy2):
        if copy1.hasSingleLength():
            copy1.highestMax = copy1.lowestMin + copy1._min_length
            copy2.lowestMin += copy2._resolution
        else:
            copy1._max_length = copy1._min_length
            copy2._min_length += copy2._resolution
        

    def _distribute(self, dom1, dom2):
        variable = self.findSmallestDomain(dom1)
        if self.verbose:
            print 'Distributing domain for variable', variable
        splitted = dom1[variable]
        cpy1 = splitted.copy()
        cpy2 = splitted.copy()

        self._split_values(cpy1, cpy2)
            
        dom1[variable] = cpy1
        dom2[variable] = cpy2
        
        return cpy1, cpy2
            
        

##
## Constraints
##    

class AbstractFIConstraint(AbstractConstraint):
    def __init__(self, var1, var2):
        AbstractConstraint.__init__(self, (var1, var2))
    
    def estimateCost(self, domains):
        return 1

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, str(self._variables))

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __hash__(self):
        # FIXME: to be able to add constraints in Sets (and compare them)
        # FIXME: improve implementation
        variables = tuple(sorted(self._variables))
        return hash((self.__class__.__name__, variables))
    
    def narrow(self, domains):
        """narrowing algorithm for the constraint"""
        dom1 = domains[self._variables[0]]
        dom2 = domains[self._variables[1]]

        return self._doNarrow(dom1, dom2)

    def _doNarrow(self, dom1, dom2):
        """virtual method which does the real work"""
        raise NotImplementedError



# FIXME: deal with more than 2 domains at once ?
class NoOverlap(AbstractFIConstraint):

    def __eq__(self, other):
        return isinstance(other, NoOverlap) and \
               set(self._variables) == set(other._variables)

    def _doNarrow(self, dom1, dom2):
        if not dom1.overlap(dom2):
            return 1
        elif dom1.no_overlap_impossible(dom2) :
            raise ConsistencyFailure
        elif dom1.lowestMax == dom2.highestMin and dom2.lowestMax > dom1.highestMin :
            dom1.setHighestMax(dom2.highestMin)
            dom2.setLowestMin(dom1.lowestMax)
            return 1
        elif dom1.lowestMax > dom2.highestMin and dom2.lowestMax == dom1.highestMin :
            dom2.setHighestMax(dom1.highestMin)
            dom1.setLowestMin(dom2.lowestMax)
            return 1
        return 0
        
class StartsBeforeStart(AbstractFIConstraint):

    def _doNarrow(self, dom1, dom2):
        
        if dom1.lowestMin > dom2.highestMin:
            raise ConsistencyFailure
        if dom1.highestMin < dom2.lowestMin:
            return 1
        return 0

class StartsBeforeEnd(AbstractFIConstraint):

    def _doNarrow(self, dom1, dom2):
        if dom1.lowestMin > dom2.highestMax:
            raise ConsistencyFailure
        if dom1.highestMin < dom2.lowestMax:
            return 1
        return 0 
    
class EndsBeforeStart(AbstractFIConstraint):

    def _doNarrow(self, dom1, dom2):
        if dom1.lowestMax > dom2.highestMin:
            raise ConsistencyFailure
        if dom1.highestMax < dom2.lowestMin:
            return 1
        if dom1.highestMax > dom2.highestMin:
            dom1.setHighestMax(dom2.highestMin)
        return 0 

class EndsBeforeEnd(AbstractFIConstraint):

    def _doNarrow(self, dom1, dom2):
        if dom1.lowestMax > dom2.highestMax:
            raise ConsistencyFailure
        if dom1.highestMax < dom2.lowestMax:
            return 1
        if dom1.highestMax > dom2.highestMax:
            dom1.setHighestMax(dom2.highestMax)
        return 0 

class StartsAfterStart(AbstractFIConstraint):

    def _doNarrow(self, dom1, dom2):
        if dom1.highestMin < dom2.lowestMin:
            raise ConsistencyFailure
        if dom1.lowestMin > dom2.highestMin:
            return 1
        if dom1.lowestMin < dom2.lowestMin:
            dom1.setLowestMin(dom2.lowestMin)
        return 0 
        
class StartsAfterEnd(AbstractFIConstraint):

    def _doNarrow(self, dom1, dom2):
        if dom1.highestMin < dom2.lowestMax:
            raise ConsistencyFailure
        if dom1.lowestMin > dom2.highestMax:
            return 1
        if dom1.lowestMin < dom2.lowestMax:
            dom1.setLowestMin(dom2.lowestMax)
        return 0 

class EndsAfterStart(AbstractFIConstraint):

    def _doNarrow(self, dom1, dom2):
        if dom1.highestMax < dom2.lowestMin:
            raise ConsistencyFailure
        if dom1.lowestMax > dom2.highestMin:
            return 1
        return 0 
    
class EndsAfterEnd(AbstractFIConstraint):

    def _doNarrow(self, dom1, dom2):
        if dom1.highestMax < dom2.lowestMax:
            raise ConsistencyFailure
        if dom1.lowestMax > dom2.highestMax:
            return 1
        return 0
    
