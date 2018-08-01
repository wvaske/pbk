import abc
from PBK.util.perflogger import LoggedObject


class DataCapture(LoggedObject, abc.ABC):

    def __init__(self, *args, **kwargs):
        """
        The init method of a DataCapture subclass should verify that all systems are set up for capturing data.

        Eg: A DataCapture for collectd should check that collectd is installed

        :param args:
        :param kwargs:
        """
        super().__init__(*args, **kwargs)

    @abc.abstractmethod
    def setup(self):
        """
        This method does any setup that we don't expect to be part of a normal system.

        Eg: A DataCapture for collectd should verify that all collects are available to run
        :return:
        """

    @abc.abstractmethod
    def teardown(self):
        """
        This method should remove any run/sequence specific files or settings from a system
        :return:
        """

    @abc.abstractmethod
    def start(self):
        """
        This method starts a data collect. Some collects will have data returned from teh start and stop and use
          the difference as the final result data. Some will only return data at the end. Regardless, start should
          NOT return data but instead hold the interim data in a file or memory structure
        :return:
        """

    @abc.abstractmethod
    def stop(self):
        """
        Stop the data collect
        :return:
        """

    @property
    @abc.abstractmethod
    def data(self):
        """
        Calling self.data will do whatever is necessary to the raw output from start and stop and return the
          'parsed/analyzed' data
        :return:
        """
