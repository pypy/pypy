"""

Special methods which we hand-generate, such as toString(), equals(), and hash().

These are generally added to methods listing of node.Class, and the
only requirement is that they must have a render(self, gen) method.

"""

import pypy.translator.jvm.typesystem as jvm
from pypy.rpython.ootypesystem import ootype, rclass

class BaseDumpMethod(object):

    def __init__(self, db, OOCLASS, clsobj):
        self.db = db
        self.OOCLASS = OOCLASS
        self.clsobj = clsobj
        self.name = "toString"
        self.jargtypes = [clsobj]
        self.jrettype = jvm.jString

    def _print_field_value(self, fieldnm, FIELDOOTY):
        self.gen.load_this_ptr()
        fieldobj = self.clsobj.lookup_field(fieldnm)
        fieldobj.load(self.gen)
        dumpmethod = self.db.toString_method_for_ootype(FIELDOOTY)
        self.gen.emit(dumpmethod)
        self.gen.emit(jvm.STRINGBUILDERAPPEND)

    def _print(self, str):
        self.gen.load_string(str)
        self.gen.emit(jvm.STRINGBUILDERAPPEND)

    def render(self, gen):
        self.gen = gen
        gen.begin_function(
            self.name, (), self.jargtypes, self.jrettype, static=False)

        gen.new_with_jtype(jvm.jStringBuilder)
        self._render_guts(gen)
        gen.emit(jvm.OBJTOSTRING)
        gen.emit(jvm.RETURN.for_type(jvm.jString))
        gen.end_function()
        self.gen = None

class InstanceDumpMethod(BaseDumpMethod):

    def _render_guts(self, gen):
        clsobj = self.clsobj
        genprint = self._print

        # Start the dump
        genprint("InstanceWrapper(")
        genprint("'" + self.OOCLASS._name + "', ")
        genprint("{")

        for fieldnm, (FIELDOOTY, fielddef) in self.OOCLASS._fields.iteritems():

            if FIELDOOTY is ootype.Void: continue
            genprint('"'+fieldnm+'":')

            # Print the value of the field:
            self._print_field_value(fieldnm, FIELDOOTY)

        # Dump close
        genprint("})")
        
class RecordDumpMethod(BaseDumpMethod):

    def _render_guts(self, gen):
        clsobj = self.clsobj
        genprint = self._print

        # We only render records that represent tuples:
        # In that case, the field names look like item0, item1, etc
        # Otherwise, we just do nothing... this is because we
        # never return records that do not represent tuples from
        # a testing function
        for f_name in self.OOCLASS._fields:
            if not f_name.startswith('item'):
                return

        # Start the dump
        genprint("StructTuple((")

        numfields = len(self.OOCLASS._fields)
        for i in range(numfields):
            f_name = 'item%d' % i
            FIELD_TYPE, f_default = self.OOCLASS._fields[f_name]
            if FIELD_TYPE is ootype.Void:
                continue

            # Print the value of the field:
            self._print_field_value(f_name, FIELD_TYPE)
            genprint(',')

        # Decrement indent and dump close
        genprint("))")

class ConstantStringDumpMethod(BaseDumpMethod):
    """ Just prints out a string """

    def __init__(self, clsobj, str):
        BaseDumpMethod.__init__(self, None, None, clsobj)
        self.constant_string = str

    def _render_guts(self, gen):
        genprint = self._print
        genprint("'" + self.constant_string + "'")

class DeepEqualsMethod(object):

    def __init__(self, db, OOCLASS, clsobj):
        self.db = db
        self.OOCLASS = OOCLASS
        self.clsobj = clsobj
        self.name = "equals"
        self.jargtypes = [clsobj, jvm.jObject]
        self.jrettype = jvm.jBool

    def render(self, gen):
        self.gen = gen
        gen.begin_function(
            self.name, (), self.jargtypes, self.jrettype, static=False)

        # Label to branch to should the items prove to be unequal
        unequal_lbl = gen.unique_label('unequal')

        gen.add_comment('check that the argument is of the correct type')
        gen.load_jvm_var(self.clsobj, 1)
        gen.instanceof(self.OOCLASS)
        gen.goto_if_false(unequal_lbl)

        gen.add_comment('Cast it to the right type:')
        gen.load_jvm_var(self.clsobj, 1)
        gen.downcast(self.OOCLASS)
        gen.store_jvm_var(self.clsobj, 1)
        
        # If so, compare field by field
        for fieldnm, (FIELDOOTY, fielddef) in self.OOCLASS._fields.iteritems():
            if FIELDOOTY is ootype.Void: continue
            fieldobj = self.clsobj.lookup_field(fieldnm)

            gen.add_comment('Compare field %s of type %s' % (fieldnm, FIELDOOTY))

            # Load the field from both this and the argument:
            gen.load_jvm_var(self.clsobj, 0)
            gen.emit(fieldobj)
            gen.load_jvm_var(self.clsobj, 1)
            gen.emit(fieldobj)

            # And compare them:
            gen.compare_values(FIELDOOTY, unequal_lbl)

        # Return true or false as appropriate
        gen.push_primitive_constant(ootype.Bool, True)
        gen.return_val(jvm.jBool)
        gen.mark(unequal_lbl)
        gen.push_primitive_constant(ootype.Bool, False)
        gen.return_val(jvm.jBool)

        gen.end_function()

class DeepHashMethod(object):

    def __init__(self, db, OOCLASS, clsobj):
        self.db = db
        self.OOCLASS = OOCLASS
        self.clsobj = clsobj
        self.name = "hashCode"
        self.jargtypes = [clsobj]
        self.jrettype = jvm.jInt

    def render(self, gen):
        self.gen = gen
        gen.begin_function(
            self.name, (), self.jargtypes, self.jrettype, static=False)

        # Initial hash: 0
        gen.push_primitive_constant(ootype.Signed, 0)

        # Get hash of each field
        for fieldnm, (FIELDOOTY, fielddef) in self.OOCLASS._fields.iteritems():
            if FIELDOOTY is ootype.Void: continue
            fieldobj = self.clsobj.lookup_field(fieldnm)

            gen.add_comment('Hash field %s of type %s' % (fieldnm, FIELDOOTY))

            # Load the field and hash it:
            gen.load_jvm_var(self.clsobj, 0)
            gen.emit(fieldobj)
            gen.hash_value(FIELDOOTY)

            # XOR that with the main hash
            gen.emit(jvm.IXOR)

        # Return the final hash
        gen.return_val(jvm.jInt)

        gen.end_function()

