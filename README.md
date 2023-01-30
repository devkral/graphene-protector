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

strawberry variant with mixin

```python 3
from graphene_protector import Limits, SchemaMixin, default_path_ignore_pattern
from strawberry import Schema

class CustomSchema(SchemaMixin, Schema):
    protector_default_limits = Limits(depth=20, selections=None, complexity=100)
    protector_path_ignore_pattern = default_path_ignore_pattern

schema = CustomSchema(query=Query)
result = schema.execute(query_string)
```

Note: for the mixin method all variables are prefixed in schema with `protector_`. Internally the `get_protector_` methods are used and mapped on the validation context

## Limits

A Limits object has following attributes:

-   depth: max depth (default: 20, None disables feature)
-   selections: max selections (default: None, None disables feature)
-   complexity: max (depth subtree \* selections subtree) (default: 100, None disables feature)

they overwrite django settings if specified.

## decorating single fields

Sometimes single fields should have different limits:

```python
    person1 = Limits(depth=10)(graphene.Field(Person))
```

Limits are inherited for unspecified parameters

## one-time disable limit checks

to disable checks for one operation use check_limits=False (works for:
execute, execute_async (if available), subscribe (if available)):

```python 3
from graphene_protector import Limits
from graphene_protector.graphene import Schema
schema = Schema(query=Query, limits=Limits(depth=20, selections=None, complexity=100))
result = schema.execute(query_string, check_limits=False)
```

# Path ignoring

This is a feature for ignoring some path parts in calculation but still traversing them.
It is useful for e.g. relay which inflates the depth significant and can cause problems with complexity
Currently it is set to `edges/node$` which reduces the depth of connections by one.
If you want to ignore all children on a path then remove $ but be warned: it can be a long path and it is still traversed.
The path the regex matches agains is composed like this: `fieldname/subfields/...`.

Other examples are:

-   `node$|id$` for ignoring id fields in selection/complexity count and reducing the depth by 1 when seeing a node field
-   `page_info|pageInfo` for ignoring page info in calculation (Note: you need only one)

Note: items prefixed with `__` (internal names) are always ignored and not traversed

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

# related projects:

-   secure-graphene: lacks django integration, some features and has a not so easy findable name.
    But I accept: it is the "not invented here"-syndrome
-

# TODO

-   stop when an open path regex is used. May append an invalid char and check if it is still ignoring
-   keep an eye on the performance impact of the new path regex checking
