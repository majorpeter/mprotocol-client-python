class NodeProperty:
    def __init__(self, client, path=[]):
        self.client = client
        self.path = path

    def get_node(self):
        return self.client.send_sync('GET /' + '/'.join(self.path))

    def get_property(self):
        return self.client.send_sync('GET /' + '/'.join(self.path[:-1]) + '.' + self.path[-1])

    def __getattr__(self, name):
        return NodeProperty(self.client, self.path + [name])

    def __str__(self):
        result = self.get_property()
        if not result:
            raise BaseException('Could not get property value: ' + str(self.path))
        return result.data['value']
