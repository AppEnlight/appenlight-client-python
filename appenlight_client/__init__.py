__version__ = '0.6.18'
__protocol_version__ = '0.5'


class AppenlightException(Exception):
    @property
    def message(self):
        return self._message

    @message.setter
    def message_set(self, message):
        self._message = message

    def __str__(self):
        return repr(self.args)


from appenlight_client.client import make_appenlight_middleware
