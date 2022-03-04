__package__ = "tests.django"
DEBUG = True
SECRET_KEY = "fake-key"
INSTALLED_APPS = [
    "graphene_django",
]
GRAPHENE_PROTECTOR_DEPTH_LIMIT = 2
GRAPHENE_PROTECTOR_SELECTIONS_LIMIT = 50
DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
}
GRAPHENE = {"SCHEMA": "tests.django.schema_graphene.schema"}
