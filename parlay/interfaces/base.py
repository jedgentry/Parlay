"""
Parlay interfaces allow generic control over different implementations.  This generic control definition allows a
host of widgets and scripts to interact with many different items, as long as the item 'implements' the interface.

From wikipedia:

 In object-oriented languages, the term 'interface' is often used to define an abstract type that contains no data or
 code, but defines behaviors as method signatures.  A class having code and data for all the methods corresponding to
 that interface is said to implement that interface.  Furthermore, a class can implement multiple interfaces, and hence
 can be of different types at the same time.

 An interface is hence a type definition; anywhere an object can be exchanged (for example, in a function or
 method call) the type of the object to be exchanged can be defined in terms of its interface rather than specifying
 a particular class.  This means that any class that implements that interface can be used.  For example, a dummy
 implementation may be used to allow development to progress before the final implementation is available.
 In another case, a fake or mock implementation may be substituted during testing.  Such stub implementations are
 replaced by real code later in the development process.

 Usually a method defined in an interface contains no code and thus cannot itself be called; it must be implemented
 by non-abstract code to be run when it is invoked.  An interface called "Stack" might define two methods: push() and
 pop().  It can be implemented in different ways, for example, FastStack and GenericStack - the first being fast,
 working with a stack of fixed size, and the second using a data structure that can be resized, but at the cost of
 somewhat lower speed.
"""


import zope.interface


class ParlayInterface(zope.interface.Interface):
    """
    Base class that all parlay interfaces should inherit from
    """
    pass
