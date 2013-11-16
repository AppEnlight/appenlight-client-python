__version__ = '0.5.15'
__protocol_version__ = '0.3.7'


class ErrormatorException(Exception):
    @property
    def message(self):
        return self._message

    @message.setter
    def message_set(self, message):
        self._message = message

    def __str__(self):
        return repr(self.args)


from errormator_client.client import make_errormator_middleware