import os
import json
import pickle
import tempfile

from collections import MutableSequence


class PersistentMutableSequence(MutableSequence, list):

    def __init__(self, init_sequence=None, filename=None, method='pickle'):
        super().__init__()
        supported_persist_methods = ['pickle', 'json']
        if method in supported_persist_methods:
            self.persist_method = method
        else:
            raise NotImplementedError(f'{method} is not a supported persist method. '
                                      f'Use one of: {supported_persist_methods}')

        if filename is None:
            self.file_descriptor, self.filename = tempfile.mkstemp()
        else:
            self.file_descriptor = None
            self.filename = filename

        # ._data is our container. We use a list as it does everything we need
        if init_sequence is not None:
            self._data = list(init_sequence)
        else:
            self._data = []

        self.persist()

    def __repr__(self):
        return repr((self._data, self.filename))

    def __setitem__(self, index, obj):
        self._data[index] = obj
        self.persist()

    def __delitem__(self, index):
        del self._data[index]
        self.persist()

    def insert(self, index, obj):
        self._data.insert(index, obj)
        self.persist()

    def persist(self):
        if self.file_descriptor is not None:
            open_file = os.fdopen(self.file_descriptor, 'w')
        else:
            open_file = open(self.filename, 'w')

        if self.persist_method is 'json':
            json.dump(self, open_file)
        elif self.persist_method is 'pickle':
            pickle.dump(self, open_file)

        open_file.flush()
        open_file.close()

    def remove_file(self):
        os.remove(self.filename)
        self.file_descriptor = None
        self.filename = None


if __name__ == "__main__":
    pass