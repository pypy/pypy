from __future__ import generators
import types
from model import SomeValue, ANN, immutable_types, debugname


class MostGeneralValue:
    def __nonzero__(self):
        return False
mostgeneralvalue = MostGeneralValue()

class ImpossibleValue(Exception):
    pass
impossiblevalue = ImpossibleValue()


class About:
    def __init__(self):
        # 'annotations' maps Predicates to tuples
        #   (SomeValue, {set-of-blocks-depending-on-this-annotation})
        self.annotations = {}
        self.subjects = {}  # set of SomeValues we are about
    def __repr__(self):    # debugging
        subjs = [debugname(c) for c in self.subjects]
        subjs.sort()
        lines = ['About %s:' % ' and '.join(subjs)]
        annotations = [(str(pred), value)
                       for pred, (value, deps) in self.annotations.items()]
        annotations.sort()
        for name, somevalue in annotations:
            lines.append('%15s --> %r' % (name, somevalue))
        return '\n'.join(lines)


class AnnotationSet:
    """An annotation set is a (large) family of annotations."""

    # This is basically a mapping {SomeValue(): About()}
    # with convenient methods.

    def __init__(self):
        self.about = {}
        self.inblock = None

    def enter(self, block, callback):
        self.inblock = block
        self.callback = callback

    def leave(self):
        self.inblock = None

    def isshared(self, val1, val2):
        return self.about.get(val1, val1) == self.about.get(val2, val2)

    def __repr__(self):     # debugging
        lines = ['=====  AnnotationSet  =====']
        abouts = [(repr(somevalue), about)
                  for somevalue, about in self.about.items()]
        abouts.sort()
        alreadyseen = {}
        for name, about in abouts:
            if about not in alreadyseen:
                if about.annotations:  # ignore empty Abouts
                    lines.append(repr(about))
                alreadyseen[about] = True
        return '\n'.join(lines)

    def get(self, predicate, subject):
        if subject is not mostgeneralvalue:
            about = self._about(subject)
            result = about.annotations.get(predicate)
            if result:
                answer, dependencies = result
                if self.inblock:
                    dependencies[self.inblock] = True
                return answer
        return mostgeneralvalue

    def _about(self, somevalue):
        try:
            return self.about[somevalue]
        except KeyError:
            if somevalue is mostgeneralvalue:
                raise ValueError, "Unexpected mostgeneralvalue"
            if isinstance(somevalue, ImpossibleValue):
                raise somevalue
            about = self.about[somevalue] = About()
            about.subjects[somevalue] = True
            return about

    def set(self, predicate, subject, answer=True):
        about = self._about(subject)
        if predicate in about.annotations:
            raise ValueError, "There is already an annotation for %r" % subject
        if answer is not mostgeneralvalue:
            about.annotations[predicate] = answer, {}

    def kill(self, predicate, subject):
        about = self._about(subject)
        if predicate in about.annotations:
            someval, deps = about.annotations[predicate]
            del about.annotations[predicate]
            # perform invalidations
            for block in deps:
                self.callback(block)

    def merge(self, oldvalue, newvalue):
        """Update the heap to account for the merging of oldvalue and newvalue.
        Return the merged somevalue."""
        if isinstance(newvalue, ImpossibleValue):
            return oldvalue
        if isinstance(oldvalue, ImpossibleValue):
            return newvalue
        if newvalue is mostgeneralvalue or oldvalue is mostgeneralvalue:
            return mostgeneralvalue
        if self.isshared(oldvalue, newvalue):
            return oldvalue

        # build an About set that is the intersection of the two incoming ones
        about1 = self._about(oldvalue)
        about2 = self._about(newvalue)
        about3 = About()
        for pred in about1.annotations:
            if pred in about2.annotations:
                someval1, dep1 = about1.annotations[pred]
                someval2, dep2 = about2.annotations[pred]
                if someval1 == someval2:
                    someval3 = someval1
                elif (isinstance(someval1, SomeValue) and
                      isinstance(someval2, SomeValue)):
                    someval3 = self.merge(someval1, someval2)
                    if someval3 is mostgeneralvalue:
                        continue
                else:
                    continue   # annotation not in common
                dep3 = dep1.copy()
                dep3.update(dep2)
                about3.annotations[pred] = someval3, dep3

        # if 'oldvalue' or 'newvalue' is immutable, we should not
        # modify the annotations about it.  If one of them is mutable,
        # then we must replace its About set with 'about3'.
        invalidatedblocks = {}
        for about in [about1, about2]:
            # find all annotations that are removed or generalized
            removedannotations = []
            for pred, (someval, deps) in about.annotations.items():
                if (pred in about3.annotations and
                    self.isshared(about3.annotations[pred][0], someval)):
                    continue   # unmodified annotation
                removedannotations.append(deps)
            # if the existing 'value' is mutable, or if nothing has been
            # removed, then we identify (by sharing) the 'value' and the
            # new 'about3'.
            if not removedannotations or ANN.immutable not in about.annotations:
                # patch 'value' to use the new 'about3'.
                for sharedvalue in about.subjects:   # this includes 'value'
                    self.about[sharedvalue] = about3
                    about3.subjects[sharedvalue] = True
                for deps in removedannotations:
                    invalidatedblocks.update(deps)

        if not about3.subjects:
            value3 = SomeValue()
            self.about[value3] = about3
            about3.subjects[value3] = True

        # perform invalidations
        for block in invalidatedblocks:
            self.callback(block)
        
        return about3.subjects.iterkeys().next()

    def settype(self, someval, knowntype):
        self.set(ANN.type, someval, knowntype)
        if knowntype in immutable_types:
            self.set(ANN.immutable, someval)

    def copytype(self, oldcell, newcell):
        self.set(ANN.type, newcell, self.get(ANN.type, oldcell))
        self.set(ANN.immutable, newcell, self.get(ANN.immutable, oldcell))
