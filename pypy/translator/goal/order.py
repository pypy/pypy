import sys
import os

lst = open('module-list', 'r')
try:
   prefixes = lst.read().split()
finally:
   lst.close()

NOMATCH = sys.maxint

def order(annotator, pending):
   cache = {}
   annotated = annotator.annotated
   def indx(block):
      func = annotated[block]
      module = func.__module__
      if module is None:
         module = 'None'
      tag = "%s:%s" % (module, func.__name__)
      try:
         return cache[tag]
      except KeyError:
         match = NOMATCH
         i = 0
         for pfx in prefixes:
            if tag.startswith(pfx):
               if match == NOMATCH:
                  match = i
               else:
                  if len(pfx) > len(prefixes[match]):
                     match = i
            i += 1
         cache[tag] = match
         return match

   pending.sort(lambda  blk1, blk2: cmp(indx(blk1), indx(blk2)))

   cur_module = ['$']
   def track(block):
      module = annotated[block].__module__
      if module != cur_module[0]:
         print "Specializing blocks in module: %s" % module
         cur_module[0] = module
   return track
   

