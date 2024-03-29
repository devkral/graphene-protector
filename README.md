# What does this project solve?

It provides protection against malicious grapqhl requests (resource exhaustion).
Despite its name it can be used with graphql (pure), graphene, strawberry.
It is implemented via a custom ValidationRule,
supports error reporting and early bail out strategies as well as limits for single fields

# Installation

```sh
pip install graphene-protector
```

# Integration

## Django

This adds to django the following setting:

-   GRAPHENE_PROTECTOR_DEPTH_LIMIT: max depth
-   GRAPHENE_PROTECTOR_SELECTIONS_LIMIT: max selections
-   GRAPHENE_PROTECTOR_COMPLEXITY_LIMIT: max (depth \* selections)
-   GRAPHENE_PROTECTOR_PATH_INGORE_PATTERN: ignore fields in calculation (but still traverse them)

Integrate with:

graphene:

```python 3
# schema.py
# replace normal Schema import with:
from graphene_protector.django.graphene import Schema
schema = Schema(query=Query, mutation=Mutation)
```

and add in django settings to GRAPHENE

```python 3

GRAPHENE = {
    ...
    "SCHEMA": "path.to.schema",
}
```

or strawberry:

```python 3
# schema.py
# replace normal Schema import with:
from graphene_protector.django.strawberry import Schema
schema = Schema(query=Query, mutation=Mutation)
```

manual way (note: import from django for including defaults from settings)

```python 3
from graphene_protector.django.graphene import Schema
# or
# from graphene_protector.django.strawberry import Schema
schema = Schema(query=Query)
result = schema.execute(query_string)
```

manual way with custom default Limits

```python 3
from graphene_protector import Limits
from graphene_protector.django.graphene import Schema
# or
# from graphene_protector.django.strawberry import Schema
schema = graphene.Schema(query=Query, limits=Limits(complexity=None))
result = schema.execute(
    query_string
)

```

## Graphene & Strawberry

limits keyword with Limits object is supported.

```python 3
from graphene_protector import Limits
from graphene_protector.graphene import Schema
# or
# from graphene_protector.strawberry import Schema
schema = Schema(query=Query, limits=Limits(depth=20, selections=None, complexity=100))
result = schema.execute(query_string)
```

## pure graphql

```python 3

from graphene_protector import LimitsValidationRule
from graphql.type.schema import Schema
schema = Schema(
    query=Query,
)
query_ast = parse("{ hello }")
self.assertFalse(validate(schema, query_ast, [LimitsValidationRule]))

```

or with custom defaults

```python 3

from graphene_protector import Limits, LimitsValidationRule
from graphql.type.schema import Schema

class CustomLimitsValidationRule(LimitsValidationRule):
    default_limits = Limits(depth=20, selections=None, complexity=100)

schema = Schema(
    query=Query,
)
query_ast = parse("{ hello }")
self.assertFalse(validate(schema, query_ast, [LimitsValidationRule]))

```

strawberry extension variant

```python 3
from graphene_protector import Limits
from graphene_protector.strawberry import CustomGrapheneProtector
from strawberry import Schema
schema = Schema(query=Query, extensions=[CustomGrapheneProtector(Limits(depth=20, selections=None, complexity=100))])
result = schema.execute(query_string)
```

or with custom defaults via Mixin

```python 3

from graphene_protector import Limits, SchemaMixin, LimitsValidationRule
from graphql.type.schema import Schema

class CustomSchema(SchemaMixin, Schema):
    protector_default_limits = Limits(depth=20, selections=None, complexity=100)

schema = CustomSchema(
    query=Query,
)
query_ast = parse("{ hello }")
self.assertFalse(validate(schema, query_ast, [LimitsValidationRule]))

```

strawberry variant with mixin (uses protector_per_operation_validation in contrast to the official graphene-protector strawberry schema)

```python 3
from graphene_protector import Limits, SchemaMixin, default_path_ignore_pattern
from strawberry import Schema

class CustomSchema(SchemaMixin, Schema):
    protector_default_limits = Limits(depth=20, selections=None, complexity=100)
    protector_path_ignore_pattern = default_path_ignore_pattern

schema = CustomSchema(query=Query)
result = schema.execute(query_string)
```

Note: for the mixin method all variables are prefixed in schema with `protector_`. Internally the `get_protector_` methods are used and mapped on the validation context. The extracted functions can be customized via the `protector_decorate_graphql_schema` method.

## Limits

A Limits object has following attributes:

-   depth: max depth (default: 20, None disables feature)
-   selections: max selections (default: None, None disables feature)
-   complexity: max (depth subtree \* selections subtree) (default: 100, None disables feature)
-   gas: accumulated gas costs (default: None, None disables feature)
-   passthrough: field names specified here will be passed through regardless if specified (default: empty frozen set)

they overwrite django settings if specified.

## decorating single fields

Sometimes single fields should have different limits:

```python
from graphene_protector import Limits
person1 = Limits(depth=10)(graphene.Field(Person))
```

Limits are passthroughs for missing parameters

There is also a novel technique named gas: you can assign a field a static value or dynamically calculate it for the field

The decorator is called gas_usage

```python
from graphene_protector import gas_usage
person1 = gas_usage(10)(graphene.Field(Person))
# dynamic way:
person2 = gas_usage(lambda **kwargs: 10)(graphene.Field(Person))

```

see tests for more examples

## one-time disable limit checks

to disable checks for one operation use check_limits=False (works for:
execute, execute_async (if available), subscribe (if available)):

```python 3
from graphene_protector import Limits
from graphene_protector.graphene import Schema
schema = Schema(query=Query, limits=Limits(depth=20, selections=None, complexity=100))
result = schema.execute(query_string, check_limits=False)
```

Usefull for debugging or working around errors

# Path ignoring

This is a feature for ignoring some path parts in calculation but still traversing them.
It is useful for e.g. relay which inflates the depth significant and can cause problems with complexity
Currently it is set to `edges/node$` which reduces the depth of connections by one.
If you want to ignore all children on a path then remove $ but be warned: it can be a long path and it is still traversed.
The path the regex matches agains is composed like this: `fieldname/subfields/...`.

Other examples are:

-   `node$|id$` for ignoring id fields in selection/complexity count and reducing the depth by 1 when seeing a node field
-   `page_info|pageInfo` for ignoring page info in calculation (Note: you need only one, in case auto_snakecase=True only `pageInfo`)

Note: items prefixed with `__` (internal names) are always ignored and not traversed.

Note: if auto_snakecase is True, the path components are by default camel cased (overwritable via explicit `camelcase_path`)

Note: gas is excluded from path ignoring

# Gas

Gas should be a positive integer. Negative integers are possible but
the evaulation is stopped whenever the counter is above the limit so this is not reliable

The gas usage is annotated with the gas_usage decorator. A function can be passed
which receives the following keyword arguments:

-   schema_field
-   fieldname
-   parent (parent of schema_field)
-   graphql_path

# full validation

On the validation rule the validation is stopped by default when an error is found
This default can be overwritten and it is modified for the django code pathes.
Whenever DEBUG is active a full validation happens, otherwise the shortcut is used.
See the source-code how to change your schema to have a custom hook for deciding if a full validation is done.
In addition the `path_ignore_pattern` and `limits` attributes can be also changed dynamically.

# hooks

The validation rule uses some `protector_` prefixed methods from the schema.
With this you can customize the default behaviour.
It is used by the django mixin to read the settings (see django) and to react on DEBUG with full_validation

# Development

I am open for new ideas.
If you want some new or better algorithms integrated just make a PR

## Internals

Path ignoring is ignored for the gas calculation (gas is always explicit). Therefor there is no way to stop when an open path was found (all children are ignored).

This project uses a "stack free" recursive approach. Instead of calling recursively, generators are used to remember the position and to continue.

Note: graphql itself will fail because they are not using a stack free approach. For graphql there was a limit around 200 depth. The graphql tree cannot be constructed so there is no way to evaluate this.

# related projects:

-   secure-graphene: lacks django integration, some features and has a not so easy findable name.
    But I accept: it is the "not invented here"-syndrome
-   cost specs: https://ibm.github.io/graphql-specs/cost-spec.html
    looks nice but very hard to implement. Handling costs at client and server side synchronously is complicated.
    Also the costs are baked into the schema, which crosses the boundary between static and dynamic

# Security Advise

Please note, that this project doesn't prevent resource exhaustion attacks by using a huge amount of tokens. This project
prevents attacks after the string has been parsed to a node graph.

Please see token limiter (e.g. strawberry.extensions TokenLimiter) for that purpose. Or set manually the token limit to an appropiate value
e.g. 1000 (ExecutionContext), see the strawbbery extension for an example

Note also, that because of the recursive parsing of strings, there is the possibility to cause an exception
by using very deep graphs (> 200 level).
Because this attack is also taking place while string parsing (string to graph), I cannot stop it.
The effects are limited because of the security features of python (stops after 1000 level depth) and returns an exception which stops the graph parsing

# TODO

-   manually construct the graphql tree for tests for check_resource_usage
-   fill RessourceLimits (graphql errors) with details like the field where the limit was reached
-   improve documentation
-   keep an eye on the performance impact of the new path regex checking
-   add tests for auto_snakecase and camelcase_path
-   skip tests in case settings are not matching
