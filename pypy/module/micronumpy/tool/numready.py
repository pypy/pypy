#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This should be run under PyPy.
"""

import platform
import subprocess
import sys
import tempfile
import webbrowser
from collections import OrderedDict

import jinja2


MODULE_SEARCH_CODE = '''
import types
import {modname} as numpy

for name in dir(numpy):
    if name.startswith("_"):
        continue
    obj = getattr(numpy, name)
    kind = "{kinds[UNKNOWN]}"
    if isinstance(obj, types.TypeType):
        kind = "{kinds[TYPE]}"
    print kind, ":", name
'''

ATTR_SEARCH_CODE = '''
import types
import {modname} as numpy

obj = getattr(numpy, "{name}")
for name in dir(obj):
    #if name.startswith("_"):
    #    continue
    sub_obj = getattr(obj, name)
    kind = "{kinds[UNKNOWN]}"
    if isinstance(sub_obj, types.TypeType):
        kind = "{kinds[TYPE]}"
    print kind, ":", name
'''

KINDS = {
    "UNKNOWN": "U",
    "TYPE": "T",
}

PAGE_TEMPLATE = u"""
<!DOCTYPE html>
<html lang="en">
    <head>
        <title>NumPyPy Status</title>
        <meta http-equiv="content-type" content="text/html; charset=utf-8">
        <style type="text/css">
            body {
                font-family: 'Consolas', 'Bitstream Vera Sans Mono', monospace;
            }
            h1 {
                text-align: center;
            }
            h3 {
                text-align: center;
            }
            table {
                border: 8px solid #DFDECB;
                margin: 30px auto;
                font-size: 12px;
            }
            table th {
                text-align: left;
            }
            table td {
                padding: 4px 10px;
                text-align: center;
            }
            .exists {
                background-color: #337792;
                color: white;
                border: 1px solid #234F61;
            }
        </style>
    </head>
    <body>
        <h1>NumPyPy Status</h1>
        <h3>Overall: {{ msg }}</h3>
        <table>
            <thead>
                <tr>
                    <th></th>
                    <th>PyPy</th>
                    <th></th>
                    <th>PyPy</th>
                    <th></th>
                    <th>PyPy</th>
                    <th></th>
                    <th>PyPy</th>
                    <th></th>
                    <th>PyPy</th>
                </tr>
            </thead>
            <tbody>
                {% for chunk in all_items %}
                    <tr>
                    {% for item in chunk %}
                        <th class='{{ item.cls }}'>{{ item.name }}</th>
                        <td class='{{ item.cls }}'>{{ item.symbol }}</td>
                    {% endfor %} 
                    </tr>
                {% endfor %}
            </tbody>
        </table>
    </body>
</html>
"""

class SearchableSet(object):
    def __init__(self, items=()):
        self._items = {}
        for item in items:
            self.add(item)

    def __iter__(self):
        return iter(self._items)

    def __contains__(self, other):
        return other in self._items

    def __getitem__(self, idx):
        return self._items[idx]

    def add(self, item):
        self._items[item] = item

    def __len__(self):
        return len(self._items)

class Item(object):
    def __init__(self, name, kind, subitems=None):
        self.name = name
        self.kind = kind
        self.subitems = subitems

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        return self.name == other.name


class ItemStatus(object):
    def __init__(self, name, pypy_exists):
        self.name = name
        self.cls = 'exists' if pypy_exists else ''
        self.symbol = u"✔" if pypy_exists else u'✖'

    def __lt__(self, other):
        return self.name < other.name

def find_numpy_attrs(python, modname, name):
    lines = subprocess.check_output(
        [python, "-c", ATTR_SEARCH_CODE.format(modname=modname, kinds=KINDS, name=name)]
    ).splitlines()
    items = SearchableSet()
    for line in lines:
        kind, name = line.split(" : ", 1)
        items.add(Item(name, kind))
    return items

def find_numpy_items(python, modname="numpy"):
    lines = subprocess.check_output(
        [python, "-c", MODULE_SEARCH_CODE.format(modname=modname, kinds=KINDS)]
    ).splitlines()
    items = SearchableSet()
    for line in lines:
        kind, name = line.split(" : ", 1)
        subitems = None
        if kind == KINDS["TYPE"]:
            if name in ['ndarray', 'dtype']:
                subitems = find_numpy_attrs(python, modname, name)
        items.add(Item(name, kind, subitems))
    return items

def split(lst):
    SPLIT = 5
    lgt = len(lst) // SPLIT + 1
    l = [[] for i in range(lgt)]
    for i in range(lgt):
        for k in range(SPLIT):
            if k * lgt + i < len(lst):
                l[i].append(lst[k * lgt + i])
    return l

def main(argv):
    cpy_items = find_numpy_items("/usr/bin/python")
    pypy_items = find_numpy_items(argv[1], "numpypy")
    all_items = []

    msg = '%d/%d names, %d/%d ndarray attributes, %d/%d dtype attributes' % (
        len(pypy_items), len(cpy_items), len(pypy_items['ndarray'].subitems),
        len(cpy_items['ndarray'].subitems), len(pypy_items['dtype'].subitems),
        len(cpy_items['dtype'].subitems))
    for item in cpy_items:
        pypy_exists = item in pypy_items
        if item.subitems:
            for sub in item.subitems:
                all_items.append(
                    ItemStatus(item.name + "." + sub.name, pypy_exists=pypy_exists and pypy_items[item].subitems and sub in pypy_items[item].subitems)
                )
        all_items.append(ItemStatus(item.name, pypy_exists=item in pypy_items))
    html = jinja2.Template(PAGE_TEMPLATE).render(all_items=split(sorted(all_items)), msg=msg)
    if len(argv) > 2:
        with open(argv[2], 'w') as f:
            f.write(html.encode("utf-8"))
    else:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(html.encode("utf-8"))
        print "Saved in: %s" % f.name

if __name__ == '__main__':
    main(sys.argv)
