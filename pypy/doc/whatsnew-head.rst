=======================
What's new in PyPy 2.6+
=======================

.. this is a revision shortly after release-2.6.1
.. startrev: 07769be4057b

.. branch: keys_with_hash
Improve the performance of dict.update() and a bunch of methods from
sets, by reusing the hash value stored in one dict when inspecting
or changing another dict with that key.
