PyPy Source Code 
================ 

.. contents::
.. sectnum::

Checking out & running PyPy as a two-liner 
------------------------------------------ 

There is no public release yet, but you can easily do:: 

    svn co http://codespeak.net/svn/pypy/dist dist-pypy 

and after checkout you can get a PyPy interpreter via:: 

    python dist-pypy/pypy/interpreter/py.py 

have fun :-) 


Browsing via HTTP and getting an svn client
-------------------------------------------

You can `browse the pypy source code`_ directly via http.
(sorry, viewcvs is still not stable enough with subversion).
And here is some information to `install a subversion client`_. 

.. _`install a subversion client`: howtosvn.html 
.. _`browse the pypy source code`: http://codespeak.net/svn/pypy/dist 


coding style and testing 
------------------------ 

We keep a strong focus on testing because we want to be able
to refactor things all the time (without proper automated 
testing this would become very hard and fragile).  

For an overview of how we organize our codebase please look at our 
`coding-style document`_.   

For running all PyPy tests you can issue:: 

    cd dist-pypy/pypy/
    python test_all.py 

test_all.py really is another name for `py.test`_ which is a testing
tool working from the current directory unless you specify 
filename/directory arguments. 

If you want to have write access to the codespeak respository
please send a mail to <b>jum at anubis han de</b> or <b>hpk at merlinux de</b>
in order to ask for a username and password.  Please mention what you want to do
within the pypy project. Even better, come to our next sprint so that we can get
to know you.  

.. _`documentation start page`: http://codespeak.net/pypy/index.cgi?doc/index.html 
.. _`coding-style document`: http://codespeak.net/pypy/index.cgi?doc/coding-style.html 
.. _`py.test`: /py/current/doc/test.html 


PyPy Documentation
==================


Viewing documentation 
---------------------

PyPy documentation is generated from reST textfiles in the pypy/documentation directory of
our pypy-subversion repository.  Go to the `documentation start page`_ and hit
"recently modified" to get a list of recently modified documents.  While in 
"doc-view" you also have a navigation area on the left side which maps all 
documentation files. 

Adding documentation 
-------------------- 

Please add new or updated documentation by checking it in to the appropriate 
directory in subversion, usually under 
http://codespeak.net/svn/pypy/dist/pypy/documentation 

+ Remember to run ``svn up`` **before** doing any commit.
+ All filenames should be lowercase, and documentation should be .txt files.
+ Mark-up the documentation with reST so it can generate a pretty html version.
+ On the server side a commit on the doc-subtree will immediately update the webpage. 

*Note*  If you don't markup the textfile, it'll still be checked in, but when docutils 
runs the parser, it'll look ugly on the website. So run docutils yourself before you commit it. 

Some reST basics:
-----------------

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

