"""
Python 3 SDK for the KATANA(tm) Platform (http://katana.kusanagi.io)

Copyright (c) 2016-2017 KUSANAGI S.L. All rights reserved.

Distributed under the MIT license.

For the full copyright and license information, please view the LICENSE
file that was distributed with this source code.

"""

__license__ = "MIT"
__copyright__ = "Copyright (c) 2016-2017 KUSANAGI S.L. (http://kusanagi.io)"

import logging

from .. import json

LOG = logging.getLogger(__name__)

# Supported parameter types
TYPE_NULL = 'null'
TYPE_BOOLEAN = 'boolean'
TYPE_INTEGER = 'integer'
TYPE_FLOAT = 'float'
TYPE_ARRAY = 'array'
TYPE_OBJECT = 'object'
TYPE_STRING = 'string'

# Parameter type names to python types
TYPE_CLASSES = {
    TYPE_BOOLEAN: bool,
    TYPE_INTEGER: int,
    TYPE_FLOAT: float,
    TYPE_ARRAY: list,
    TYPE_OBJECT: dict,
    TYPE_STRING: str,
    }


class Param(object):
    """Parameter class for API.

    A Param object represents a parameter received for an action in a call
    to a Service component.

    """

    def __init__(self, name, **kwargs):
        self.__value = kwargs.get('value') or ''
        self.__name = name

        self.__type = kwargs.get('datatype')
        if self.__type not in TYPE_CLASSES:
            self.__type = TYPE_STRING
        elif not self.__type:
            self.__type = self.resolve_type(self.__value)

        self.__exists = kwargs.get('exists', False)

    @classmethod
    def resolve_type(cls, value):
        """Converts native types to schema types.

        :param value: The value to analyze.
        :type value: mixed

        :rtype: str

        """

        if value is None:
            return TYPE_NULL

        value_class = value.__class__
        if value_class == bytes:
            return TYPE_STRING
        elif value_class in (tuple, set):
            return TYPE_ARRAY

        for type_name, cls in TYPE_CLASSES.items():
            if value_class == cls:
                return type_name

        return TYPE_OBJECT

    def get_name(self):
        """Get aprameter name.

        :rtype: str

        """

        return self.__name

    def get_type(self):
        """Get parameter data type.

        :rtype: str

        """

        return self.__type

    def get_value(self):
        """Get parameter value.

        Value is returned using the parameter data type for casting.

        :returns: The parameter value.
        :rtype: mixed

        """

        name = self.get_name()
        type_ = self.get_type()
        error_msg = 'Param "{}" value is not a {}'.format(name, type_)
        try:
            value = self.__value
            if type_ == 'string':
                value = '"{}"'.format(value)

            value = json.deserialize(value)
        except:
            LOG.error('Param "%s" is not %s: %s', name, type_, value)
            raise TypeError(error_msg)

        if not isinstance(value, TYPE_CLASSES[type_]):
            raise TypeError(error_msg)

        return value

    def exists(self):
        """Check if parameter exists.

        :rtype: bool

        """

        return self.__exists

    def copy(self, **kwargs):
        """Create a copy of current object.

        :param name: Parameter name.
        :type name: str
        :param value: Parameter value.
        :type value: str
        :param type: Parameter data type.
        :type type: str

        :rtype: `Param`

        """

        return self.__class__(
            kwargs.get('name', self.__name),
            value=kwargs.get('value', self.__value),
            type=kwargs.get('type', self.__type),
            )

    def copy_with_name(self, name):
        return self.copy(name=name)

    def copy_with_value(self, value):
        return self.copy(value=value)

    def copy_with_type(self, datatype):
        return self.copy(type=datatype)
