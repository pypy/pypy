=====================
PyPy Documentation
=====================

PyPy documentation is generated from reST textfiles in the /doc directory of
our pypy-subversion repository.  On the pypy home page you'll find a "doc" link that
shows you a list of recently modified documents.  While in "doc-view" you also have
a navigation area on the left side which maps all documentation. 

Please add new or updated documentation by checking it in to the appropriate 
directory in subversion, usually under http://codespeak.net/svn/pypy/trunk/doc/.  

+ Remember to run ``svn up`` **before** doing any commit.
+ All filenames should be lowercase, and documentation should be .txt files.
+ Mark-up the documentation with reST so it can generate a pretty html version.
+ On the server side a commit on the doc-subtree will immediately update the webpage. 

*Note*  If you don't markup the textfile, it'll still be checked in, but when docutils 
runs the parser, it'll look ugly on the website. So run docutils yourself before you commit it. 

Some reST basics:
------------------

There should be a title on your page. Do it like this::

 Here is my Title
 ==================

 Here is a section title
 -------------------------

Make sure you have a blank line after your = or - lines or it will give you an error.
For marking a block of code so it'll look right, you can::

 Put a line of text ending with ::
  indent your code at least one space
  my code
    more code
      even more code
  still more code

End of the "block" occurs whenever you unindent back to the same level as the
text with the ``::`` at the end.

Using an underscore after a word like this_ will make reST think you want a hyperlink.
To avoid that (especially with things like ``wrap_``), you can use the `` back quote ``
to mark it as plain text.

You can get more info on reST markup at http://docutils.sourceforge.net/docs/rst/quickref.html

------------------------
Checking your work
------------------------

In order to make sure that what you commit looks reasonably pretty (or at least not
entirely broken), you'll need to run the ``docutils`` parser on it. Unless you've
installed it in the past, you probably don't have it installed. Open IDLE (or any
Python interactive environment) and try "import docutils". If it imports, hooray!
Otherwise, you'll need to download it.

Go to sourceforge and download the ``snapshot`` version. Install it.

*Note to Debian users:* Be sure you installed ``python2.2-dev``, which includes ``distutils``,
before trying to install ``docutils``.

Once you have ``docutils`` installed, you can use it go to your shell and use it like this::

 $ python ~/mypath/docutils/tools/buildhtml.py
 /// Processing directory: /home/anna/downloads/arObjSpaceDoc
     ::: Processing .txt: howtosvn.txt
     ::: Processing .txt: index.txt

**WARNING** This will process **all** text documents in the directory and any subdirectories.
I prefer to work on text in a separate directory, run the ``docutils`` parser to see what it
looks like, then copy the .txt file over to my local /doc checkouts to commit it.

Use a browser menu to go to ``File: Open: filename.html`` then you can see what it looks
like. Look at the command shell to see what errors you've got on which lines and fix it
in your textfile. You can then re-run the buildhtml.py script and see what errors you get.
After it's fixed, you can commit the .txt file and it'll automagically be turned into html
viewable on the website.


Here are some sample reST textfiles to see what it looks like:

+ ObjectSpace_
+ ObjectSpaceInterface_

---------------------------------------------------------------------------------

.. _this: http://docutils.sourceforge.net/docs/rst/quickref.html
.. _ObjectSpace: objspace/objspace.html 
.. _ObjectSpaceInterface: objspace/objspaceinterface.html

