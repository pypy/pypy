guiding design/implementation ideas
-----------------------------------

Annotation aims at providing type inference to RPython programs. 
Annotation works from the flowmodel of a program. (A flowmodel
can be viewed as an information-preserving 'dead code' representation
of a program.)  

Annotation mainly deals with connecting interesting information
to SomeValue's which are instances of a very simple class::

   class SomeValue:
        pass

A SomeValue represents a possible state within a program. 
Any information about the type or more specific information
like being a constant is done by an Annotation. E.g. the
an int-type annotation is expressed like this: 

   Annotation(op.type, someval1, someval2)
   Annotation(op.constant(int), someval2)

Note especially how the constant-ness of someval2 encodes the
information 'someval2 is exactly int'.  SomeValue's are values on which
little is known by default, unless Annotation's are used to restrict
them. 

Keep in mind that the more Annotation's you have on SomeValue, the more
restricted it is, i.e. the less real values it can represent.  A newly
created SomeValue() has no annotation by default, i.e. can represent
anything at all.  At the other extreme, there is a special
'blackholevalue' that behaves as if it had all Annotation's set on it;
it stands for an impossible, non-existent value (because all these
Annotations are contradictory). The name 'blackholevalue' reminds you
that during type inference SomeValue's start with a lot of annotations
(possibly as a 'blackholevalue'), and annotations are killed -- less
annotations, more possibilities. 

Annotations are stored in a global list, which is an AnnotationSet instance.  AnnotationSet provides (via Transactions) methods to query, add and kill annotations.  It also manages "sharing": two different SomeValue's can be later found to be identical (in the Python sense of "is"), and the AnnotationSet can be taught about this.
