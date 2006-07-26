import py

testpath = py.magic.autopath().dirpath()
packagepath = testpath.dirpath()
py.std.sys.path.append(str(packagepath.dirpath()))
