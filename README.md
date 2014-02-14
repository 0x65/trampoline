<p>python famously doesn't have <a href="http://en.wikipedia.org/wiki/Tail_call">tail call optimization</a>, with no plans to add it anytime soon. the reason, as guido van rossum points out, is that TCO destroys the stack and makes debugging harder. this is true, and it's also true that in a lot of cases, it's easy to rewrite your function to take constant space.</p>

<p>what if we don't want to rewrite our function, but still benefit from TCO? there have been a <a href="http://code.activestate.com/recipes/474088/">couple</a> <a href="http://code.activestate.com/recipes/496691/">attempts</a> at this, but they suffer from a couple problems. first, and perhaps most obvious, is that they do not provide true tail call optimization, but merely tail recursion optimization (note: at least the ones I found from a cursory google search). and second, they introduce runtime overhead. can we do better?</p>

<p>there are a couple ways to traditionally implement tail calls. we'll do it with a standard method called trampolining. a trampoline is essentially a function that calls other functions. the functions that the trampoline calls have a function call in tail position, and are rewritten so that instead of calling the function, they return the function to be called and its parameters back to the trampoline. the trampoline then calls this function and the process repeats. it is easy to see that the stack space this uses is constant: a frame for the trampoline, and an additional frame for the currently executing function.</p>

<p>so how can we rewrite tail calls in this way in python? it's not pretty, but we can use the <a href="http://docs.python.org/2/library/ast.html">ast</a> module to rewrite whatever functions we want "optimized." first, we get the program's AST:</p>

<pre>
from ast import *
from inspect import getsource

def factorial(n, acc=1):
    if n == 1: return acc
    return factorial(n-1, n*acc)

ast = parse(getsource(factorial))
</pre>

<p>now that we have the AST, we can subclass the NodeTransformer class to recursively walk the tree and modify the nodes for return statements:</p>

<pre>
class TrampolineTransform(NodeTransformer):
    def visit_Return(self, node):
        return_val = node.value

        if return_val.__class__ == Call:
            func = return_val.func
            func_args = return_val.args

            return copy_location(Return(
                value=Tuple(elts=[
                    Str(s='__trampoline'),
                    func,
                    List(elts=func_args, ctx=Load())
                ], ctx=Load()), ctx=Load()
            ), node)

        return node
</pre>

<p>we only modify the nodes that have an immediate call as their return value. if it was, for example, a BinOp instead of a Call, we know that the call is not really in tail position, so we leave it alone. ignoring some of the plumbing needed for modifying the AST, you can see we just return a tuple consisting of a sentinel value, the function object, and its positional arguments. we ignore star args and keyword args here for simplicity, it is trivial to add them to the tuple.</p>

<p>now that we have the proper AST, we can just compile it and write a trampoline function:</p>

<pre>
tco_ast = fix_missing_locations(TrampolineTransform().visit(ast))
exec compile(tco_ast, __name__, 'exec')

def trampoline(start):
    ret = start()
    while isinstance(ret, tuple) and ret[0] == '__trampoline':
        _, func, args = ret
        ret = func(*args)
    return ret
</pre>

<p>we visit the AST and make the changes to return statements. we then call compile() to generate for us a python code object, and use exec to execute the code object in the current namespace. the trampoline function is as described above: it takes a function to run, and while the results of that function call are a tuple with the sentinel value, we keep applying the returned function and arguments. if the function returns something else (like factorial does in the base case), we simply exit the trampoline.</p>

<p>does it work?</p>

<pre>
>>> trampoline(lambda: factorial(10000))
284625968091705451890641321211986889014805... it's a really big number
</pre>

<p>hooray! it runs (reasonably quickly, too). what's even better, it works for functions that have tail calls but aren't tail recursive, like the typical mutually recursive functions odd and even. it's not perfect -- stuff like inspect.getsource and exec get in the way too much -- but it is an interesting exerise. if you want to check out the complete source for this, it's available <a href="https://github.com/0x65/trampoline">here</a>.</p>
