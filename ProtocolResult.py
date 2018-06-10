import re

## Contains the result of a command
class ProtocolResult:
    ok_init_str = 'E0:Ok'

    ## Constructor
    # @param response_line the result of the command that is received from the device
    # @param data optional additional data to be stored in this object
    def __init__(self, response_line, data=None):
        match = re.match('^E([0-9]):', response_line)
        if match:
            self.ordinal = int(match[1])
            self.message = response_line.split(':')[1]
            self.data = data
        elif response_line.startswith('P_') or response_line.startswith('PW_'):
            self.ordinal = 0
            self.message = 'Ok'

            self.data = {
                'type': response_line[response_line.index('_')+1:response_line.index(' ')],
                'value': response_line[response_line.index('=')+1:]
            }
        else:
            raise ValueError('Invalid response line: %s' % response_line)

    ## Checks whether a received line is a valid response for a command
    # @param response_line received line
    # @return True if it is valid
    @staticmethod
    def is_valid_result(response_line):
        if re.match('^E([0-9]):', response_line):
            return True
        if response_line.startswith('P_'):
            return True
        if response_line.startswith('PW_'):
            return True
        return False

    ## Converts object to bool so that it can be used in if statements
    # @note The result 'Ok' is converted to True, any error is converted to False
    def __bool__(self):
        return self.ordinal == 0

    ## Converts the object to a human-readable form
    def __str__(self):
        str = '%s (Code: %d)' % (self.message, self.ordinal)
        if self.data:
            str += ' (Data: %s)' % self.data
        return str
