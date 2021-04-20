# What does this project solve?

It is a small backend for a graphql schema which protects against malicious requests.

The current logic is simple and efficient (early bail out)

# Installation

```
pip install graphene-protector
```

# Integration

## Django

### Project's wide limits

This adds to django following settings:

- GRAPHENE_PROTECTOR_DEPTH_LIMIT: max depth
- GRAPHENE_PROTECTOR_SELECTIONS_LIMIT: max selections
- GRAPHENE_PROTECTOR_COMPLEXITY_LIMIT: max (depth \* selections)

Integrate with:

```python 3
# schema.py
# replace normal Schema import with:
from graphene_protector.django import Schema
schema = Schema(query=Query, mutation=Mutation)
```

and add in django settings to GRAPHENE

```python 3

GRAPHENE = {
    ...
    "SCHEMA": "path.to.schema",
}
```

manual way

```python 3
from graphene import Schema
from graphene_protector.django import ProtectorBackend
backend = ProtectorBackend()
schema = graphene.Schema(query=Query)
result = schema.execute(query_string, backend=backend)

```

### Limits per operation

Beside project's wide limits set with `GRAPHENE_PROTECTOR_*`, it is also
possible to set those limits per operation (per query or mutation).

To setup limits per operation, just add `limit_${operation}` attribute to your
`Query` or `Mutation` object. For example:

```python 3
from graphene_protector.django import Limits

class UserType(DjangoObjectType):
    # ...

class Query(graphene.ObjectType):
    users = graphene.List(UserType)
    limit_users = Limits(depth=1, selections=3, complexity=None)
    # ...
```

Following keywords arguments are supported in `Limits` object:
- `depth`: max depth
- `selections`: max selections
- `complexity`: max (depth subtree \* selections subtree)

These keywords, *if specified*, overwrite `GRAPHENE_PROTECTOR_*` (django) settings.

If none of these keywords nor `GRAPHENE_PROTECTOR_*` settings are specified, the default values are
- `depth`: 20
- `selections`: `None`
- `complexity`: 100

Using `None` in one of these fields disables the feature.

## Other/Manually

```python 3
from graphene_protector import ProtectorBackend, Limits
backend = ProtectorBackend(limits=Limits(depth=20, selections=None, complexity=100))
schema = graphene.Schema(query=Query)
result = schema.execute(query_string, backend=backend)

```

# Development

I am open for new ideas.
If you want some new or better algorithms integrated just make a PR

# related projects:

- secure-graphene: lacks django integration, some features and has a not so easy findable name.
  But I accept: it is the "not invented here"-syndrome
