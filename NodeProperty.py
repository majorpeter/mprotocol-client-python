## This class allows easy access to nodes and properties
from mprotocol_client_python.ProtocolResult import ProtocolResult


class NodeProperty:
    actual_attributes = ['_client', '_path', '_parent', '_sync', '_children']

    ## Constructor
    # @param client instance of Client class (serial interface)
    # @param path array of parent nodes / property name
    def __init__(self, client, path=[], parent=None, sync=True):
        self._client = client
        self._path = path
        self._parent = parent
        self._sync = sync
        self._children = None

    ## Returns the node's or property's name (last element of path array)
    def get_name(self):
        if len(self._path) > 0:
            return self._path[-1]
        return '/'

    ## Returns manual string of node
    def get_node_manual(self):
        return self._client.send_sync('MAN ' + self.get_path_as_node()).data

    ## Returns manual string of property
    def get_property_manual(self):
        return self._client.send_sync('MAN ' + self.get_path_as_property()).data

    ## Returns the nodes whole path
    def get_path_as_node(self):
        return '/' + ' / '.join(self._path)

    ## Returns the node property's whole path
    # @note same as get_path_as_node, except for appending the last part with a dot instead
    def get_path_as_property(self):
        return '/' + '/'.join(self._path[:-1]) + '.' + self._path[-1]

    ## Returns the whole path of the node's or property's parent node
    def get_parent_path(self):
        return '/' + ' / '.join(self._path[:-1])

    ## Returns child nodes
    def get_children(self):
        if not self._children:
            self.fetch_children()

        return self._children

    ## Returns a set of ProtocolResult's containing the properties of the node
    def get_properties(self):
        result = self.protocol_get_node()
        if not result:
            raise BaseException('Could not get property value: ' + str(self._path))
        property_set = []
        for line in result.data:
            if line.startswith('P'):
                property_set.append(ProtocolResult(line))
        return property_set

    ## Registers a callback to this property's changes
    # @param callback the function to be called when the property changes
    #                 signature: callback_function(property_name, new_value)
    def subscribe_to_changes(self, callback):
        self._client.add_subscription(callback, self.get_parent_path(), self.get_name())

    ## Unregisters the callback from this property's changes
    def unsubscribe_from_changes(self, callback):
        self._client.remove_subscription(callback, self.get_parent_path(), self.get_name())

    ## Registers a callback to any property's changes in this node
    # @param callback the function to be called when a property of this node changes
    #                 signature: callback_function(property_name, new_value)
    def subscribe_to_all_property_changes(self, callback):
        self._client.add_subscription(callback, self.get_path_as_node())

    ## Unregisters a callback from this node's changes
    def unsubscribe_from_all_property_changes(self, callback):
        self._client.remove_subscription(callback, self.get_path_as_node())

    ## Sends a GET message for this node
    def protocol_get_node(self):
        command = 'GET ' + self.get_path_as_node()
        if not self._sync:
            raise BaseException('Cannot use GET in async node (%s)' % command)
        return self._client.send_sync(command)

    ## Sends a GET message for this property
    def protocol_get_property_value(self):
        command = 'GET ' + self.get_path_as_property()
        if not self._sync:
            raise BaseException('Cannot use GET in async node (%s)' % command)
        return self._client.send_sync(command)

    ## Sends a CALL message for this method
    # @param argument optional single string argument of method
    def protocol_call_method(self, argument = None):
        cmd = 'CALL ' + self.get_path_as_property()
        if argument:
              cmd += '=' + argument

        if self._sync:
            result = self._client.send_sync(cmd)
            return result
        else:
            self._client.send_async(cmd)

    ## Updates the _children array of this instance from device
    def fetch_children(self):
        result = self.protocol_get_node()
        if not result:
            raise BaseException('Could not fetch children for: %s' % str(self.get_path_as_node()))

        self._children = []
        for line in result.data:
            if line.startswith('N '):
                child_node_name = line[2:]
                self._children.append(NodeProperty(client=self._client, path=self._path + [child_node_name], parent=self, sync=self._sync))

    ## This override allows access to nodes' children by name as if it were an attribute of the node
    def __getattr__(self, name):
        return NodeProperty(client=self._client, path=self._path + [name], parent=self, sync=self._sync)

    ## This override allows setting property values by '='
    def __setattr__(self, key, value):
        if key in NodeProperty.actual_attributes:
            object.__setattr__(self, key, value)
        else:
            if self._sync:
                result = self._client.send_sync('SET /' + '/'.join(self._path) + '.' + key + '=' + value)
                if not result:
                    raise BaseException('Could not set property value: %s, %s=%s, Error: %s' % \
                                        (str(self._path), key, value, str(result)))
            else:
                self._client.send_async('SET /' + '/'.join(self._path) + '.' + key + '=' + value)

    ## This override implements lazy evaluation of GET messages (reads current value of the property and returns is)
    def __str__(self):
        result = self.protocol_get_property_value()
        if not result:
            raise BaseException('Could not get property value: ' + str(self._path))
        return result.data['value']

    ## This override allows calling protocol methods with 'function(parameter)' syntax
    def __call__(self, *args, **kwargs):
        if len(args) > 1:
            raise BaseException('Too many args in method call: ' + str(self._path))

        arg = ''
        if len(args) == 1:
            arg = str(args[0])
        return self.protocol_call_method(arg)

    ## This override allows iteration over a node's children (e.g. 'for child in node:')
    def __getitem__(self, item):
        if type(item) == 'str':
            return str(getattr(self, item))

        if not self._children:
            self.fetch_children()

        return self._children[item]

    ## This override allows setting property values using the array subscript syntax
    def __setitem__(self, key, value):
        setattr(self, key, value)
