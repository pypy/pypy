import py

packagedir = py.magic.autopath().dirpath().dirpath()
py.std.sys.path.append(str(packagedir.dirpath()))
