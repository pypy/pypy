#!/usr/bin/env python

from math import pi
import os

from pypy.rpython.lltypesystem import rffi
from pypy.translator.c.test.test_genc import compile
from pypy.tool.udir import udir

import py.test
import distutils.errors

py.test.skip("this is using rctypes, so not working currently")

try:
    from pypy.rlib.rcairo._cairo import CAIRO_FORMAT_ARGB32
    from pypy.rlib.rcairo.ll_cairo import *
except distutils.errors.CompileError, e:
    py.test.skip("Probably cairo not found: " + str(e))

def demo(filename):
    width = 800
    height = 600
    surface = cairo_image_surface_create(CAIRO_FORMAT_ARGB32,width,height)
    cr = cairo_create(surface)
    cairo_scale(cr, width, height)
    cairo_set_line_width(cr, 0.04)

    
    cairo_arc(cr, 0.5, 0.5, 0.3, 0, 2 * pi)
    cairo_clip(cr)
    
    cairo_new_path(cr) # current path is not
                       # consumed by cairo_clip()
    cairo_rectangle(cr, 0, 0, 1, 1)
    cairo_fill(cr)
    cairo_set_source_rgb(cr, 0, 1, 0)
    cairo_move_to(cr, 0, 0)
    cairo_line_to(cr, 1, 1)
    cairo_move_to(cr, 1, 0)
    cairo_line_to(cr, 0, 1)
    cairo_stroke(cr)

    #_cairo_surface_write_to_png(surface, 'foo.png') # XXX why does this fail to compile ??
    path = rffi.str2charp(filename)
    cairo_surface_write_to_png(surface, path)
    rffi.free_charp(path)

    cairo_destroy(cr)
    cairo_surface_destroy(surface)
    return 0

def _cairo_surface_write_to_png(surface, path):
    path = rffi.str2charp(path)
    cairo_surface_write_to_png(surface, path)
    rffi.free_charp(path)


def llstr_from_str(s):
    return s.chars  # ???

def test_ll_cairo_run():
    filename = str(udir.join('foo.png'))
    demo(filename)
    open(filename)
    os.unlink(filename)

def test_ll_cairo_compile():
    _demo = compile(demo, [str])
    filename = str(udir.join('foo.png'))
    _demo(filename)
    open(filename)
    os.unlink(filename)





