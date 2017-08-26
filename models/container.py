from collections import deque
from .time import SparkTime
from json.decoder import JSONDecodeError
from ..utils import is_api_id


class SparkContainer(object):
    ''' Generic Generator Container '''

    def __init__(self, cls, parent=None, session=None):
        self._cls = cls
        self._parent = parent
        self._created = SparkTime()
        self._generator = self._make_generator()
        self._items = deque()
        self._finished = False
        self._session = session or self.parent.session

    @property
    def cls(self):
        return self._cls

    @property
    def created(self):
        return self._created

    @property
    def parent(self):
        return self._parent

    @property
    def session(self):
        return self._session

    def __getitem__(self, key):
        # List style lookups
        if isinstance(key, int):
            while len(self._items) <= key and not self._finished:
                try:
                    self._generator.__next__()
                except StopIteration:
                    if len(self._items) < key:
                        raise IndexError(f'{self} index out of range')
                    else:
                        return self.cls(**self._items[key])
            return self.cls(**self._items[key])

        # Dict sytle lookups
        elif isinstance(key, str) and is_api_id(key):
            items = [item for item in self._items if item.id == key]
            if items:
                return items[0]
            else:
                resp = self.session.get(self.cls.api_base + key)
                return self.cls(**resp.json())
        else:
            raise TypeError('Indices must be an int or Spark API ID')

    def _make_generator(self, params={}):
        assert isinstance(params, dict)
        response = self.session.get(self.cls.api_base, params=params)
        data = response.json()
        items = deque(data.get('items', []))
        while items:
            item = items.popleft()
            self._items.append(item)
            yield item

            if not items:
                if response.links.get('next'):
                    response = self.session.get(response.links['next']['url'])
                    items.extend(response.json()['items'])
                else:
                    self._finished = True
                return

    def __repr__(self):
        return f'SparkContainer({self.cls.api_base}'
