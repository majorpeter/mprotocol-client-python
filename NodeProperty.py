class NodeProperty:
    def __init__(self, client, path=[]):
        self._client = client
        self._path = path

    def get_node(self):
        return self._client.send_sync('GET /' + '/'.join(self._path))

    def get_property(self):
        return self._client.send_sync('GET /' + '/'.join(self._path[:-1]) + '.' + self._path[-1])

    def __getattr__(self, name):
        return NodeProperty(self._client, self._path + [name])

    def __setattr__(self, key, value):
        if key in ['_client', '_path']:
            object.__setattr__(self, key, value)
        else:
            result = self._client.send_sync('SET /' + '/'.join(self._path) + '.' + key + '=' + value)
            if not result:
                raise BaseException('Could not set property value: %s, %s=%s' % (str(self._path), key, value))

    def __str__(self):
        result = self.get_property()
        if not result:
            raise BaseException('Could not get property value: ' + str(self._path))
        return result.data['value']
