

class _DataObject:

    def __init__(self, **kwargs):
        object.__setattr__(self, '_data', {})
        # ^^^ self._data = ... would cause infinite recursion because of __setattr__
        for field in self._fields:
            assert isinstance(field, str)
            self._data[field] = kwargs.pop(field) if field in kwargs else None
        assert not kwargs, repr(kwargs)

    def __repr__(self):
        return '<{cls} {data}>'.format(cls=self.__class__.__name__, data=self._data)

    def __getattr__(self, name):
        try:
            return self._data[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def __setattr__(self, name, value):
        assert name in self._fields
        self._data[name] = value


class HostedZone (_DataObject):

    _fields = ('id', 'name', 'comment', 'rrs_count')


def hosted_zone_from_aws(raw_hz):
    try:
        return HostedZone(
            id=raw_hz['Id'],
            name=raw_hz['Name'],
            comment=raw_hz['Config'].get('Comment'),
            rrs_count=raw_hz['ResourceRecordSetCount'])
    except Exception as e:
        raise Exception('Failed to create HostedZone from AWS data: {!r}'.format(raw_hz)) from e
