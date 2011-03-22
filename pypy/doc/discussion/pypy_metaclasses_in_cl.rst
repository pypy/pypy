IRC log
=======

::

    [09:41] <dialtone> arigo: is it possible to ask the backendoptimizer to completely remove all the oogetfield('meta', obj)?
    [09:42] <dialtone> and at the same time to change all the oogetfield('somefield', meta) into oogetfield('somefield', obj)
    [09:42] <dialtone> because then we wouldn't need the metaclass hierarchy anymore
    [09:42] <dialtone> (at least in common lisp)
    [09:42] <arigo> as far as I know the idea was indeed to be able to do this kind of things
    [09:43] <arigo> but not necessarily in the existing backendopt
    [09:44] <dialtone> uhmmm
    [09:44] <dialtone> I have no idea how to do this stuff
    [09:44] <arigo> if I understand it correctly, as a first step you can just tweak gencl to recognize oogetfield('meta', obj)
    [09:44] <dialtone> I'll think about it on the plane maybe
    [09:44] <arigo> and produce a same_as equivalent instead
    [09:44] <arigo> (do I make any sense at all?)
    [09:44] <dialtone> yes
    [09:45] <dialtone> same_as(meta, obj)
    [09:45] <dialtone> so that the next oogetfield() will still work on meta which in reality is the obj
    [09:45] <arigo> yes
    [09:45] <dialtone> thus you obtained the same thing without removing anything
    [09:45] <dialtone> cool
    [09:46] <antocuni> dialtone: can you explain me better what are you trying to do?
    [09:46] <dialtone> it looks kinda simple
    [09:46] <dialtone> am I a fool?
    [09:46] <dialtone> antocuni: I want to get rid of the metaclass stuff in common lisp
    [09:47] <dialtone> since common lisp supports class variables
    [09:47] <dialtone> (DEFCLASS foo () ((bar :allocate :class)))
    [09:47] <antocuni> cool
    [09:47] <dialtone> but to do that I also have to get rid of the opcodes that work on the object model
    [09:48] <dialtone> at first I thought about removing the metaclass related operations (or change them) but armin got a great idea about using same_as
    [09:48] idnar (i=mithrand@unaffiliated/idnar) left irc: Remote closed the connection
    [09:48] <arigo> there might be a few problems, though
    [09:48] <dialtone> and here comes the part I feared
    [09:48] <arigo> I'm not sure if the meta object is used for more than oogetfields
    [09:49] <arigo> and also, let's see if there are name clashes in the fields
    [09:49] <antocuni> I can't understand a thing: are you trying to lookup some fields in the obj directly, instead of in the metclass, right?
    [09:49] <dialtone> antocuni: yes
    [09:50] <antocuni> why an object should have fields that belongs to its metaclass?
    [09:50] <dialtone> arigo: uhmmm you can have both a class variable and an instance variable named in the same way?
    [09:50] <dialtone> metaclass is not a real metaclass
    [09:50] <arigo> I don't know
    [09:50] <braintone> arigo - r26566 - Support geterrno() from rctypes to genc.
    [09:50] <antocuni> dialtone: ah, now I understand
    [09:50] <arigo> I would expect it not to be the case, as the names come from RPython names
    [09:51] <dialtone> arigo: indeed
    [09:51] <dialtone> but I guess I can set different accessors maybe for class level things and for instance level things
    [09:51] <dialtone> let's try
    [09:51] <dialtone> no...
    [09:52] <dialtone> so a name clash would break stuff
    [09:52] <dialtone> but... how do you recognize an access to a class variable and one to an instance variable from RPython?
    [09:53] <arigo> dialtone: I think we don't have name clashes, because there is some mangling anyway
    [09:53] <dialtone> cool
    [09:53] <arigo> if I see it correctly, class variable names start with 'pbc' and instance ones with 'o'
    [09:53] <dialtone> that's what we've done in gencl yes
    [09:54] <arigo> ? that's what the ootyping is doing
    [09:54] <dialtone> yes yes
    [09:54] <arigo> :-)
    [09:54] <dialtone> I mean that I see the distinction in gencl :)
    [09:54] <dialtone> sooooooo
    [09:55] <dialtone> if I have a getfield where the first argument is meta and I simply emit the same code that I emit for the same_as I should be safe removing all the meta stuff... maybe
    [09:55] <dialtone> seems like a tiny change in gencl
    [09:55] <arigo> dialtone: in RPython, the annotator says that attributes are instance fields as soon as they are written to instances, otherwise they are class attributes
    [09:56] <arigo> yes, it should work
    [09:56] Palats (n=Pierre@izumi.palats.com) left irc: Read error: 104 (Connection reset by peer)
    [09:56] <dialtone> unless of course metaclasses are used for something else than class variables
    [09:56] <arigo> ideally, you should not look for the name 'meta' but for some other hint
    [09:57] <arigo> I'm not completely at ease with the various levels of ootype
    [09:57] <dialtone> neither am I\
    [09:57] <nikh> all field names other than those defined by ootype (like "meta") will be mangled, so i guess checking for "meta" is good enough
    [09:57] <dialtone> and I also have to ignore the setfield opcode that deals with metaclasses
    [09:58] <dialtone> or make it a same_as as well
    [09:59] <arigo> apparently, the meta instances are used as the ootype of RPython classes
    [10:00] <arigo> so they can be manipulated by RPython code that passes classes around
    [10:01] <arigo> I guess you can also pass classes around in CL, read attributes from them, and instantiate them
    [10:01] <dialtone> yes
    [10:01] <arigo> so a saner approach might be to try to have gencl use CL classes instead of these meta instances
    [10:03] <dialtone> uhmmmmm
    [10:03] <arigo> which means: recognize if an ootype.Instance is actually representing an RPython class (by using a hint)
    [10:03] <dialtone> I also have to deal with the Class_
    [10:03] <dialtone> but that can probably be set to standard-class
    [10:03] <arigo> yes, I think it's saner to make, basically, oogetfield('class_') be a same_as
    [10:04] <dialtone> cool
    [10:04] <dialtone> I think I'll save this irc log to put it in the svn tree for sanxiyn
    [10:04] <nikh> to recognize RPython class represenations: if the ootype.Instance has the superclass ootypesystem.rclass.CLASSTYPE, then it's a "metaclass"
    [10:04] <dialtone> he is thinking about this in the plane (at least this is what he told)
    [10:05] <arigo> :-)
    [10:05] <arigo> nikh: yes
    [10:05] <arigo> ootype is indeed rather complicated, level-wise, to support limited languages like Java
    [10:05] <nikh> unfortunately, yes
    [10:05] <nikh> well, in a way it's very convenient for the backends
    [10:05] <nikh> but if you want to use more native constructs, it gets hairy quickly
    [10:05] <dialtone> I dunno
    [10:05] <dialtone> depends on the backend
    [10:06] <arigo> hum, there is still an information missing that gencl would need here
    [10:06] <dialtone> I think if the language of the backend is powerful enough it could use an higher abstraction
    [10:07] <arigo> dialtone: yes, there is also the (hairly to implement) idea of producing slightly different things for different back-ends too
    [10:07] <dialtone> using backendopts?
    [10:08] <dialtone> would it make sense to have a kind of backend_supports=['metaclasses', 'classvariables', 'first_class_functions'...]
    [10:08] <arigo> maybe, but I was thinking about doing different things in ootypesystem/rclass already
    [10:08] <arigo> yes, such a backend_supports would be great
    [10:09] <nikh> dialtone: there is still an hour left to sprint, so go go go ;)
    [10:09] <nikh> you can do it, if you want it ;)
    [10:09] <arigo> what is missing is the link from the concrete Instance types, and which Instance corresponds to its meta-instance
    [10:10] idnar (i=mithrand@unaffiliated/idnar) joined #pypy.
    [10:10] <arigo> dialtone: it's not as simple as making an oogetfield be a same_as
    [10:10] <dialtone> KnowledgeUnboundError, Missing documentation in slot brain
    [10:10] <arigo> right now for CL the goal would be to generate for a normal Instance, a DEFCLASS whose :allocate :class attributes are the attributes of the meta-Instance
    [10:11] <nikh> we could optionally have class fields in Instances, and then operations like ooget/setclassfield
    [10:11] <dialtone> the reason why I ask is that if we manage to do this then we could also use default Condition as Exception
    [10:11] <dialtone> and we could map the Conditions in common lisp to exceptions in python transparently
    [10:12] <dialtone> since the object systems will then match (and they are vaguely similar anyway)
    [10:12] <arigo> nice
    [10:12] <dialtone> at least I think
    [10:18] <arigo> I'm still rather confused by ootypesystem/rclass
    [10:18] <arigo> although I think that blame would show my name on quite some bits :-)
    [10:19] <arigo> there are no class attributes read through instances
    [10:19] <arigo> they are turned into method calls
    [10:19] <arigo> accessor methods
    [10:20] <arigo> it's a bit organically grown
    [10:20] <arigo> accessor methods were introduced at one point, and the meta-Instance later
    [10:21] <dialtone> uhmmm
    [10:22] <nikh> what was the reason for having accessor methods?
    [10:22] <nikh> they seem to be only generated for class vars that are overriden in subclasses.
    [10:22] <arigo> yes
    [10:22] <arigo> before we had the meta-Instance trick, it was the only way to avoid storing the value in all instances
    [10:22] <nikh> aha
    [10:23] <nikh> we could possibly get rid of these accessors
    [10:23] <arigo> now, yes, by storing the values in the meta-Instance
    [10:23] <nikh> they are alway anyway stored in the meta-Instance, I think
    [10:23] <arigo> no, I think that other values are stored in the meta-Instance right now
    [10:24] <arigo> it's the values that are only ever accessed with a syntax 'ClassName.attr', i.e. not through an instance
    [10:24] <arigo> ...more precisely, with 'x = ClassName or OtherClassName; x.attr'
    [10:25] <nikh> hm, i'm still trying to read this out of the code ...
    [10:28] <arigo> it's in ClassRepr._setup_repr()
    [10:28] <arigo> there is no clsfields here, just pbcfields
    [10:28] <arigo> # attributes showing up in getattrs done on the class as a PBC
    [10:28] <nikh> i see
