#! /usr/bin/env python

import types
import __builtin__
builtinitems = vars(__builtin__).iteritems
import sys

typesdone = {}
exports = []

def dotype(synonym):
    typeobject = getattr(types, synonym)
    if type(typeobject) is not type: return
    exports.append(synonym)
    if typeobject in typesdone:
        print 'setattr(_types, %r, %s)' % (synonym, typeobject.__name__)
        print
        return
    typesdone[typeobject] = 1

    typename = typeobject.__name__
    typetitle = typename.title()
    print 'class %s(object):' % typename
    print
    print '''    def __new__(cls, *args):
        if cls is %s:
            return pypy.%sObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.%sObjectFactory, args)

    def __repr__(self):
        return str(self)
''' % (typename, typetitle, typetitle)

    sys.stdout.write('_register(pypy.%sObjectFactory, %s'%(typetitle, typename))

    for n, v in builtinitems():
        if v is typeobject:
            if n != typename:
                sys.stdout.write(', in_builtin=%r' % n)
            break
    else:
        sys.stdout.write(', in_builtin=False')

    default_synonym = typetitle + 'Type'
    if synonym != default_synonym:
        sys.stdout.write(', synonym=%r' % synonym)
    sys.stdout.write(')\n')

    print
    print

for synonym in dir(types):
    dotype(synonym)
print
print '__all__ = %r' % exports

