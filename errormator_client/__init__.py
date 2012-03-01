class ErrormatorException(Exception):

    @property
    def message(self):
        return self._message

    @message.setter
    def message_set(self, message):
        self._message = message

    def __str__(self):
        return repr(self.args)
