
t = Translation(entry_point[,<options>])
t.annotate([<options>])
t.rtype([<options>])
t.backendopt[_<backend>]([<options>])
t.source[_<backend>]([<options>])
f = t.compile[_<backend>]([<options>])

and t.view(), t.viewcg()

<backend> = c|llvm (for now)
you can skip steps

<options> = argtypes (for annotation) plus 
            keyword args:  gc=...|policy=<annpolicy> etc



