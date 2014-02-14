from ast import *
from inspect import getsource

# NodeTransformer objects recursively walk an AST, visiting nodes
# and potentially modifying them
class TrampolineTransform(NodeTransformer):

    # visit_Return is called whenever a return statement is encountered in the AST
    def visit_Return(self, node):
        return_val = node.value

        # if the immediate value of a return statement is a Call, we know that
        # the call is in tail position
        if return_val.__class__ == Call:

            # when evaluated, this will be the function to be called
            func = return_val.func

            # these are the (positional) arguments passed in. for simplicity, we 
            # ignore *starargs and **kwargs for now
            func_args = return_val.args

            # we modify the node so that it returns instead a tuple consisting
            # of the placeholder '__trampoline', the function to be called,
            # and its arguments
            return copy_location(Return(
                value=Tuple(elts=[
                    Str(s='__trampoline'), 
                    func, 
                    List(elts=func_args, ctx=Load())
                ], ctx=Load()), ctx=Load()
            ), node)

        # if it's not a tail call, don't modify the return statement
        return node


def trampoline(start):
    ret = start()

    # while we get return args with the trampoline placeholder,
    # we know that the function is making tail calls
    while isinstance(ret, tuple) and ret[0] == '__trampoline':
        _, func, args = ret
        ret = func(*args)

    return ret


def factorial(n, acc=1):
    if n == 1: return acc
    return factorial(n-1, n*acc)


def odd(n):
    if n == 1: return True
    return even(n-1)


def even(n):
    if n == 1: return False
    return odd(n-1)


def compile_tco(f):
    ast = parse(getsource(f))
    tco_ast = fix_missing_locations(TrampolineTransform().visit(ast))
    return compile(tco_ast, __name__, 'exec')


exec compile_tco(factorial)
exec compile_tco(odd)
exec compile_tco(even)

print trampoline(lambda: factorial(10000))
print trampoline(lambda: even(59392))
