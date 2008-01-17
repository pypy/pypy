package pypy;

public class AbstractMethodException extends Exception {

	public AbstractMethodException(){
		super("Cannot call RPython abstract methods");
	}
}
