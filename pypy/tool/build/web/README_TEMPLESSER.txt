Templesser
===========

What is it?
-----------

Templesser is basically an extension to string interpolation that introduces
blocks that can be repeated and conditional blocks.

Blocks start with '%(<name>)[b', where <name> is the name of the block,
and end with '%(<name>)]b', where <name> is again the name of the block
and must match the opening name.

The 'b' in the previous case marks a basic repeat block, which is repeated for
all items in a list; there are also 'c' (conditional) blocks that are rendered
only if the value for the context key resolves to False (and not to an empty
string).

This module is a drop-in replacement for Templess' basic functionality,
see the Templess documentation (http://templess.johnnydebris.net) for more
details.

Let's show some examples, the first displays how Templesser can do
normal string interpolation::

  >>> from pypy.tool.build.web.templesser import template
  >>> t = template(u'foo %(bar)s baz')
  >>> t.unicode({'bar': 'qux'})
  u'foo qux baz'

The second example displays how to deal with a simple conditional block::

  >>> t = template(u'foo %(bar)[cbar %(bar)]cbaz')
  >>> t.unicode({'bar': False})
  u'foo baz'
  >>> t.unicode({'bar': True})
  u'foo bar baz'

Now an example with a repeat block, note how the context value is a list
type - this can be any type of iterable, but _must_ be a list type, even
if there's only a single item to interpolate::

  >>> t = template(u'foo %(bar)[b %(bar)]b baz')
  >>> t.unicode({'bar': [1, 2, 3]})
  u'foo 1 2 3 baz'

A more useful example with a repeat block uses nested dictionaries as
values for the list, resulting in a nested interpolation::

  >>> t = template(u'foo %(bar)[b%(baz)s qux %(quux)s%(bar)]b quuux')
  >>> t.unicode({'bar': [{'baz': 1, 'quux': 2},
  ...                    {'baz': 'spam', 'quux': 'eggs'}]})
  u'foo 1 qux 2 spam qux eggs quuux'

Some quick notes
=================

* yes, this is ugly stuff...

* my motivation? simplicity... it's inspired on templess
  (http://templess.johnnydebris.net) which does similar things
  but with a more elegant (XML based) syntax, we decided to remove
  the templess dependency, but i didn't feel like modifying the
  code too much, so i wanted to have something very simple with the
  same api and similar behaviour

* there has been no time spent on error reporting at all, so
  it most probably sucks...

Questions, remarks, etc.
=========================

For questions, remarks, bug reports and patches, send email to
guido@merlinux.de.

