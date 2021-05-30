__package__ = "tests.django"
DEBUG = True
SECRET_KEY = "fake-key"
INSTALLED_APPS = [
    "graphene_django",
]
GRAPHENE_PROTECTOR_DEPTH_LIMIT = 2
GRAPHENE_PROTECTOR_SELECTIONS_LIMIT = None
