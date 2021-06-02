__package__ = "tests"

import unittest

from graphene_protector import Limits, ProtectorBackend

#
from graphql.backend.base import GraphQLBackend, GraphQLDocument
from .graphql.schema import schema


class TestCore(unittest.TestCase):
    def test_simple(self):
        backend = ProtectorBackend(
            limits=Limits(depth=2, selections=None, complexity=None)
        )
        self.assertIsInstance(backend, GraphQLBackend)
        document = backend.document_from_string(schema, "{ hello }")
        self.assertIsInstance(document, GraphQLDocument)
        result = document.execute()
        self.assertFalse(result.errors)
        self.assertDictEqual(result.data, {"hello": "World"})
