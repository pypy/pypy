package pypy;

/**
 * This interface has no function but to serve as a documentation
 * point and marker.  All the interfaces which inherit from it are
 * "callback" interfaces: that means that they are used to allow the
 * standalone Java code to invoke methods defined in the RPython code.
 * 
 * Whenever a standalone RPython module has a signature that might
 * fit as one of the appropriate callbacks, it simply implements required
 * interface.  Note that these callback interfaces are simply hard-coded
 * into database.  A more flexible mechanism may eventually be required.
 * 
 * As an example, consider {@link HashCode}.  Any time that we generate
 * a standalone method which returns a signed integer and takes a single
 * object, we cause it to implement {@link HashCode}, which then allows it
 * to be used in an {@link #RDict}. 
 * 
 * These callback functions are hard-coded in jvm/typesystem.py.  To add
 * new ones simply add items to the list.
 * 
 * @author Niko Matsakis <niko@alum.mit.edu>
 */
public interface Callback {

}
