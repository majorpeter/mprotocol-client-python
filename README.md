# MProtocol client library in Python 3

This library can be used to interface with devices that use `MProtocol` control. The protocol's `GET`/`SET`/`CALL`/`OPEN`/`CLOSE` are hidden by simple Python code of assignments and function calls etc.

## Usage

To establish a TCP connection to the target device,
```python
client = Client(ip_address, port, timeout_sec)
```

Suppose we have a `TIME` node under the root, with a property `UpTime`. To read this property,
```python
# This is lazy evaluation:
#   client.root.TIME.UpTime is just a reference that holds the information
#   about the connection and the path of the property. It has to be converted
#   to string to actually read its value. That is what print does internally.
print(client.root.TIME.UpTime)
```

Suppose we have `CANVAS` node as well, with the property `ColorHex` and the method `setRed` under it. To set the property,
```python
client.root.CANVAS.ColorHex = 'ffffff'
# or if the property name is in a variable
prop_name = 'ColorHex'
client.root.CANVAS[prop_name] = 'ffffff'
```

To call the method,
```python
client.root.CANVAS.setRed()
# or with an argument
client.root.CANVAS.setRed(42)
```

If you would like to about a property's changes,
```python
def prop_change_callback(prop, value):
    print('New value of %s is %s' % (prop, value))

client.root.CANVAS.ColorHex.subscribe_to_changes(prop_change_callback)

# and when not interested anymore
client.root.CANVAS.ColorHex.unsubscribe_from_changes(prop_callback)

# or you may attach a single callback to any property's change under a node
client.root.CANVAS.subscribe_to_all_property_changes(prop_change_callback)

# and when not interested anymore
client.root.CANVAS.unsubscribe_from_all_property_changes(prop_change_callback)
```

The client can also be used **asynchronously**, so that it will not wait for protocol responses (only TCP).
This option is of course only valid for `SET` and `CALL` opertaions, where the result may be ignored.
To send commands asynchronously, use `root_async` instead of `root`, e.g.:
```python
client.root_async.CANVAS.ColorHex = 'ffffff'
client.root_async.CANVAS.setRed()
```