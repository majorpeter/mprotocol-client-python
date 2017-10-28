class NodeProperty:
    actual_attributes = ['_client', '_path', '_children']

    def __init__(self, client, path=[]):
        self._client = client
        self._path = path
        self._children = None

    def get_name(self):
        if len(self._path) > 0:
            return self._path[-1]
        return '/'

    def get_path_as_node(self):
        return '/' + ' / '.join(self._path)

    def get_path_as_property(self):
        return '/' + '/'.join(self._path[:-1]) + '.' + self._path[-1]

    def protocol_get_node(self):
        return self._client.send_sync('GET ' + self.get_path_as_node())

    def protocol_get_property_value(self):
        return self._client.send_sync('GET ' + self.get_path_as_property())

    def protocol_call_method(self, argument):
        cmd = 'CALL ' + self.get_path_as_property()
        if argument:
              cmd += '=' + argument
        result = self._client.send_sync(cmd)
        return result

    def fetch_children(self):
        result = self.protocol_get_node()
        if not result:
            raise BaseException('Could not fetch children for: %s' % str(self._path))

        self._children = []
        for line in result.data:
            if line.startswith('N '):
                child_node_name = line[2:]
                self._children.append(NodeProperty(self._client, self._path + [child_node_name]))

    def __getattr__(self, name):
        return NodeProperty(self._client, self._path + [name])

    def __setattr__(self, key, value):
        if key in NodeProperty.actual_attributes:
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
        if type(item) == 'str':
            return str(getattr(self, item))

        if not self._children:
            self.fetch_children()

        return self._children[item]

    def __setitem__(self, key, value):
        setattr(self, key, value)
