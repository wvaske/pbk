import abc


class DescriptorClass(abc.ABC):

    def __init__(self, prop_name):
        self.prop_name = prop_name

    @abc.abstractmethod
    def __set__(self, instance, value):
        """
        Set needs to be defined in subclasses for this to work as a real discriptor
        :param instance:
        :param value:
        :return:
        """

    def __get__(self, instance, owner):
        return instance.__dict__[self.prop_name]

    def __del__(self, instance):
        del instance.__dict__[self.prop_name]


class TypeChecked(DescriptorClass):

    def __init__(self, allowed_type, prop_name, allow_none=True):
        super().__init__(prop_name=prop_name)
        self.allowed_type = allowed_type
        self.allow_none = allow_none

    def __set__(self, instance, value):
        if value is None and self.allow_none:
            pass
        elif not isinstance(value, self.allowed_type):
            raise TypeError(f'Value: "{value}" is not of the required type: {str(self.allowed_type)}')

        instance.__dict__[self.prop_name] = value


class ValueChecked(DescriptorClass):

    def __init__(self, allowed_values, prop_name, allow_none=True):
        super().__init__(prop_name=prop_name)
        self.allowed_values = allowed_values
        self.allow_none = allow_none

    def __set__(self, instance, value):
        if value is None and self.allow_none:
            pass
        elif value not in self.allowed_values:
            raise ValueError(f'Value: "{value}" is not of the available options: {str(self.allowed_values)}')

        instance.__dict__[self.prop_name] = value
