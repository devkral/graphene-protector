# What does this project solve?

It is a small backend for a graphql schema which protects against malicious requests.

The current logic is simple and efficient (early bail out)

# Installation

```sh
pip install graphene-protector
# in case of python <3.7
#pip install dataclasses
```

# Integration

## Django

This adds to django the following setting:

-   GRAPHENE_PROTECTOR_DEPTH_LIMIT: max depth
-   GRAPHENE_PROTECTOR_SELECTIONS_LIMIT: max selections
-   GRAPHENE_PROTECTOR_COMPLEXITY_LIMIT: max (depth \* selections)

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

manual way (note: import from django for including defaults from settings)

```python 3
from graphene_protector.django import Schema
schema = Schema(query=Query)
result = schema.execute(query_string)

```

manual way with custom default Limits aand operation specific limits

```python 3
from graphene_protector import Limits
from graphene_protector.django import Schema
schema = graphene.Schema(query=Query, limits=Limits())
result = schema.execute(
    query_string, backend=backend, limits=Limits(complexity=1)
)

```

## Graphene

limits keyword with Limits object is supported.

```python 3
from graphene_protector.base import Limits
from graphene_protector.graphene import Schema
backend = Schema(query=Query, limits=Limits(depth=20, selections=None, complexity=100))
result = schema.execute(query_string)
```

## pure graphql

TODO


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

# Development

I am open for new ideas.
If you want some new or better algorithms integrated just make a PR

# related projects:

-   secure-graphene: lacks django integration, some features and has a not so easy findable name.
    But I accept: it is the "not invented here"-syndrome


# TODO
-   test mutations