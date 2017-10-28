class NodeProperty:
    def __init__(self, client, path=[]):
        self._client = client
        self._path = path

    def protocol_get_node(self):
        return self._client.send_sync('GET /' + '/'.join(self._path))

    def protocol_get_property_value(self):
        return self._client.send_sync('GET /' + '/'.join(self._path[:-1]) + '.' + self._path[-1])

    def protocol_call_method(self, argument):
        cmd = 'CALL /' + '/'.join(self._path[:-1]) + '.' + self._path[-1]
        if argument:
              cmd += '=' + argument
        result = self._client.send_sync(cmd)
        return result

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
        result = self.protocol_get_property_value()
        if not result:
            raise BaseException('Could not get property value: ' + str(self._path))
        return result.data['value']

    def __call__(self, *args, **kwargs):
        if len(args) > 1:
            raise BaseException('Too many args in method call: ' + str(self._path))

        arg = ''
        if len(args) == 1:
            arg = str(args[0])
        return self.protocol_call_method(arg)

    def __getitem__(self, item):
        return str(getattr(self, item))

    def __setitem__(self, key, value):
        setattr(self, key, value)
