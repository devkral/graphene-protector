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

manual way (note: import from django for including defaults from settings)

```python 3
from graphene import Schema
from graphene_protector.django import ProtectorBackend
backend = ProtectorBackend()
schema = graphene.Schema(query=Query)
result = schema.execute(query_string, backend=backend)

```

manual way with custom Limits

```python 3
from graphene import Schema
from graphene_protector import Limits
from graphene_protector.django import ProtectorBackend
backend = ProtectorBackend(limits=Limits())
schema = graphene.Schema(query=Query)
result = schema.execute(query_string, backend=backend)

```

## Other/Manually

limits keyword with Limits object ist supported:

- depth_limit: max depth (default: 20, None disables feature)
- selections_limit: max selections (default: None, None disables feature)
- complexity_limit: max (depth subtree \* selections subtree) (default: 100, None disables feature)

they overwrite django settings if specified

```python 3
# note: Limits import from graphene_protector not from django
from graphene_protector import ProtectorBackend, Limits
backend = ProtectorBackend(limits=Limits(depth_limit=20, selections_limit=None, complexity_limit=100))
schema = graphene.Schema(query=Query)
result = schema.execute(query_string, backend=backend)

```

# Development

I am open for new ideas.
If you want some new or better algorithms integrated just make a PR

# related projects:

- secure-graphene: lacks django integration, some features and has a not so easy findable name.
  But I accept: it is the "not invented here"-syndrome
