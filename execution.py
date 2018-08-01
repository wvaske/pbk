import abc

from PBK.util.perflogger import LoggedObject
from PBK.util.descriptors import TypeChecked, ValueChecked
from PBK.util.persist import PersistentMutableSequence


class PersistentTypeChecked(TypeChecked):

    def __set__(self, instance, value):
        super().__set__(instance, value)
        instance.persist()

    def __del__(self, instance):
        super().__del__(instance)
        instance.persist()


class PersistentValueChecked(ValueChecked):

    def __set__(self, instance, value):
        super().__set__(instance, value)
        instance.persist()

    def __del__(self, instance):
        super().__del__(instance)
        instance.persist()


class TestList:
    """
    I need a definition so pycharm doesn't yell at me when I check this in TestResult
    """
    pass


class TestResult:

    def __init__(self, *args, **kwargs):
        pass

    def write_to_datastore(self):
        """
        This method will write data to the datastore following my standard process
        :return:
        """


class TestExecutor(abc.ABC, LoggedObject):

    STATUSES = ['completed', 'pending', 'failed']
    result = PersistentTypeChecked(allowed_type=TestResult, prop_name='result', allow_none=True)
    parent = PersistentTypeChecked(allowed_type=TestList, prop_name='parent', allow_none=True)
    status = PersistentValueChecked(allowed_values=STATUSES, prop_name='status', allow_none=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @abc.abstractmethod
    def setup(self):
        """
        Method to handle setup processes for a single test execution
        :return:
        """

    @abc.abstractmethod
    def teardown(self):
        """
        Method to handle teardown processes for a single test execution
        :return:
        """

    @abc.abstractmethod
    def execute(self):
        """
        The self.execute method should set the self.result and self.status properties and return the result object

        :return:
        """


class TestList(PersistentMutableSequence):

    member_type = TestExecutor

    def __init__(self, *args, **kwargs):
        """
        TestList is effectively a version of PersistentMutableSequence that checks the type of member objects
        and assigns a value to the members' 'parent' attribute so that members can call the .persist() method

        :param args:
        :param kwargs:
        """
        super().__init__(*args, **kwargs)

    @staticmethod
    def _check_obj_type(obj):
        if not isinstance(obj, TestList.member_type):
            raise TypeError(f'Members of TestList must be of type {TestList.member_type}, not {type(obj)}')

    def _set_member_parent(self, index):
        self[index].parent = self

    def __setitem__(self, index, value):
        self._check_obj_type(value)
        super().__setitem__(index, value)
        self._set_member_parent(index)

    def insert(self, index, value):
        self._check_obj_type(value)
        super().insert(index, value)
        self._set_member_parent(index)


class TestSequence(abc.ABC):

    test_list = TypeChecked(TestList, "test_list")

    def __init__(self):
        pass

    @abc.abstractmethod
    def execute_next(self):
        """
        Method to execute the next pending test

        :return:
        """

    def build_test_list(self):
        """
        This builds out the standard set of all combinations. I think there is a combinations function
        in python we can use for this

        :return:
        """
        raise NotImplementedError
