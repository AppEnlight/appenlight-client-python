import pkg_resources
from appenlight_client.utils import Version
str_version = pkg_resources.get_distribution('appenlight_client').version
__version__ = Version(str_version)
__protocol_version__ = Version('0.5.0')


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
