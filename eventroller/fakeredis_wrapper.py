"""
FakeRedis doesn't seem to work perfectly with django-redis at the moment
so this accomodates that hackily for now.
"""

from fakeredis import FakeStrictRedis
from django_redis.client import DefaultClient
from django_redis.serializers.pickle import PickleSerializer
from django_redis.compressors.identity import IdentityCompressor


class StupidRedis(DefaultClient):
    _fake = FakeStrictRedis()

    def __init__(self, server, params, backend):
        self._options = {}
        self._backend = backend
        self._serializer = PickleSerializer({})
        self._compressor = IdentityCompressor({})

    def get_client(self, *args, **kwargs):
        return self._fake

    def close(self, **kw):
        return
