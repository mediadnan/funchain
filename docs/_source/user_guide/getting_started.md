# Getting started

## Using ``chain()``
The main utility provided by `funchain` is [``chain()``](#funchain.chain),
this function is used to compose functions and compile them to a ready 
to use function-like object.

This function acts like a smart constructor that generates a specific `funchain` node,
this objects can be called _like a function_ with a single argument, and passes the
result of one function to the next, then returns the last function's result as result.

Let's consider these two python functions :

````python
def increment(num: int) -> int:
    return num + 1

def double(num: int) -> int:
    return num * 2
````

We can create a simple chain like this:

````python
from funchain import chain

calculate = chain(increment, double, increment)
````

Now ``calculate`` is a function that increments a number, then doubles it and then increments
it again; So if we try it we will get this

````pycon
>>> calculate(5)    # ((5 + 1) * 2) + 1
13
>>> calculate(8)    # ((8 + 1) * 2) + 1
19
````

This same functionality can be achieved simply by writing
````python
calculate = lambda num: increment(double(increment(num)))
````
However, there some key differences about this approach and the 
one with ``chain()``, and one of them is containing errors inside the function.

````pycon
>>> increment(double(increment(None)))
Traceback (most recent call last):
    ...
TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'
>>> calculate = chain(increment, double, increment)
>>> calculate(None)  # None

````
The chain object didn't raise the exception and returned ``None`` as alternative result,
but this **doesn't** mean that errors get completely ignored,
they can be retrieved if a <a href="https://failures.readthedocs.io/en/latest/api_ref.html#failures.Reporter" target="_blank">Reporter [⮩]</a>
object is passed after the input argument, that reporter can be later reviewed and properly handled.

## Reporting failures
To gather execution failures from a chain, we will pass a ``Reporter`` object to ``calculate``

{emphasize-lines="4"}
````pycon
>>> from failures import Reporter
>>> # or (from funchain import Reporter) same...
>>> reporter = Reporter("calculate")
>>> calculate(None, reporter)

>>> failure = reporter.failures[0]
>>> failure.source
'calculate.increment'
>>> failure.error
TypeError("unsupported operand type(s) for +: 'NoneType' and 'int'")
>>> failure.details
{'input': None}
````
``reporter.failures`` is a list of reported failures, in this case we only have 1,
the error was reported with the label ``'calculate.increment'`` that reveals its location,
and the input that caused it, which is ``None``.

```{important}
It is **highly recommended** to pass reporters to `funchain` chains and nodes,
especially in production, otherwise the errors will be permanently silenced.
```