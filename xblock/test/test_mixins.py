"""
Tests of the XBlock-family functionality mixins
"""
import ddt as ddt
from datetime import datetime
import pytz
from lxml import etree
import mock
from unittest import TestCase

from xblock.core import XBlock
from xblock.fields import List, Scope, Integer, String, ScopeIds, UNIQUE_ID, DateTime
from xblock.field_data import DictFieldData
from xblock.mixins import ScopedStorageMixin, HierarchyMixin, IndexInfoMixin
from xblock.runtime import Runtime


class AttrAssertionMixin(TestCase):
    """
    A mixin to add attribute assertion methods to TestCases.
    """
    def assertHasAttr(self, obj, attr):
        "Assert that `obj` has the attribute named `attr`."
        self.assertTrue(hasattr(obj, attr), "{!r} doesn't have attribute {!r}".format(obj, attr))

    def assertNotHasAttr(self, obj, attr):
        "Assert that `obj` doesn't have the attribute named `attr`."
        self.assertFalse(hasattr(obj, attr), "{!r} has attribute {!r}".format(obj, attr))


class TestScopedStorageMixin(AttrAssertionMixin, TestCase):
    "Tests of the ScopedStorageMixin."

    class ScopedStorageMixinTester(ScopedStorageMixin):
        """Toy class for ScopedStorageMixin testing"""

        field_a = Integer(scope=Scope.settings)
        field_b = Integer(scope=Scope.content)

    class ChildClass(ScopedStorageMixinTester):
        """Toy class for ModelMetaclass testing"""
        pass

    class FieldsMixin(object):
        """Toy mixin for field testing"""
        field_c = Integer(scope=Scope.settings)

    class MixinChildClass(FieldsMixin, ScopedStorageMixinTester):
        """Toy class for ScopedStorageMixin testing with mixed-in fields"""
        pass

    class MixinGrandchildClass(MixinChildClass):
        """Toy class for ScopedStorageMixin testing with inherited mixed-in fields"""
        pass

    def test_scoped_storage_mixin(self):

        # `ModelMetaclassTester` and `ChildClass` both obtain the `fields` attribute
        # from the `ModelMetaclass`. Since this is not understood by static analysis,
        # silence this error for the duration of this test.
        # pylint: disable=E1101
        self.assertIsNot(self.ScopedStorageMixinTester.fields, self.ChildClass.fields)

        self.assertHasAttr(self.ScopedStorageMixinTester, 'field_a')
        self.assertHasAttr(self.ScopedStorageMixinTester, 'field_b')

        self.assertIs(self.ScopedStorageMixinTester.field_a, self.ScopedStorageMixinTester.fields['field_a'])
        self.assertIs(self.ScopedStorageMixinTester.field_b, self.ScopedStorageMixinTester.fields['field_b'])

        self.assertHasAttr(self.ChildClass, 'field_a')
        self.assertHasAttr(self.ChildClass, 'field_b')

        self.assertIs(self.ChildClass.field_a, self.ChildClass.fields['field_a'])
        self.assertIs(self.ChildClass.field_b, self.ChildClass.fields['field_b'])

    def test_with_mixins(self):
        # Testing model metaclass with mixins

        # `MixinChildClass` and `MixinGrandchildClass` both obtain the `fields` attribute
        # from the `ScopedStorageMixin`. Since this is not understood by static analysis,
        # silence this error for the duration of this test.
        # pylint: disable=E1101

        self.assertHasAttr(self.MixinChildClass, 'field_a')
        self.assertHasAttr(self.MixinChildClass, 'field_c')
        self.assertIs(self.MixinChildClass.field_a, self.MixinChildClass.fields['field_a'])
        self.assertIs(self.FieldsMixin.field_c, self.MixinChildClass.fields['field_c'])

        self.assertHasAttr(self.MixinGrandchildClass, 'field_a')
        self.assertHasAttr(self.MixinGrandchildClass, 'field_c')
        self.assertIs(self.MixinGrandchildClass.field_a, self.MixinGrandchildClass.fields['field_a'])
        self.assertIs(self.MixinGrandchildClass.field_c, self.MixinGrandchildClass.fields['field_c'])


class TestHierarchyMixin(AttrAssertionMixin, TestCase):
    "Tests of the HierarchyMixin."

    class HasChildren(HierarchyMixin):
        """Toy class for ChildrenModelMetaclass testing"""
        has_children = True

    class WithoutChildren(HierarchyMixin):
        """Toy class for ChildrenModelMetaclass testing"""
        pass

    class InheritedChildren(HasChildren):
        """Toy class for ChildrenModelMetaclass testing"""
        pass

    def test_children_metaclass(self):
        # `HasChildren` and `WithoutChildren` both obtain the `children` attribute and
        # the `has_children` method from the `ChildrenModelMetaclass`. Since this is not
        # understood by static analysis, silence this error for the duration of this test.
        # pylint: disable=E1101

        self.assertTrue(self.HasChildren.has_children)
        self.assertFalse(self.WithoutChildren.has_children)
        self.assertTrue(self.InheritedChildren.has_children)

        self.assertHasAttr(self.HasChildren, 'children')
        self.assertNotHasAttr(self.WithoutChildren, 'children')
        self.assertHasAttr(self.InheritedChildren, 'children')

        self.assertIsInstance(self.HasChildren.children, List)
        self.assertEqual(Scope.children, self.HasChildren.children.scope)
        self.assertIsInstance(self.InheritedChildren.children, List)
        self.assertEqual(Scope.children, self.InheritedChildren.children.scope)


class TestIndexInfoMixin(AttrAssertionMixin):
    """
    Tests for Index
    """
    class IndexInfoMixinTester(IndexInfoMixin):
        """Test class for index mixin"""
        pass

    def test_index_info(self):
        self.assertHasAttr(self.IndexInfoMixinTester, 'index_dictionary')
        with_index_info = self.IndexInfoMixinTester().index_dictionary()
        self.assertFalse(with_index_info)
        self.assertTrue(isinstance(with_index_info, dict))


@ddt.ddt
class TestXmlSerializationMixin(TestCase):
    """ Tests for XmlSerialization Mixin """

    class TestXBlock(XBlock):
        """ XBlock for XML export test """
        etree_node_tag = 'test_xblock'

        field = String()
        simple_default = String(default="default")
        force_export = String(default="default", force_export=True)
        unique_id_default = String(default=UNIQUE_ID)
        unique_id_force_export = String(default=UNIQUE_ID, force_export=True)

    class TestXBlockWithDateTime(XBlock):
        """ XBlock for DateTime fields export """
        etree_node_tag = 'test_xblock_with_datetime'

        datetime = DateTime(default=None)

    def _make_block(self, block_type=None):
        """ Creates a test block """
        block_type = block_type if block_type else self.TestXBlock
        runtime_mock = mock.Mock(spec=Runtime)
        scope_ids = ScopeIds("user_id", block_type.etree_node_tag, "def_id", "usage_id")
        return block_type(runtime_mock, field_data=DictFieldData({}), scope_ids=scope_ids)

    def _assert_node_attributes(self, node, expected_attributes):
        """ Checks XML node attributes to match expected_attributes"""
        node_attributes = node.keys()
        node_attributes.remove('xblock-family')

        self.assertEqual(node.get('xblock-family'), self.TestXBlock.entry_point)
        self.assertEqual(set(node_attributes), set(expected_attributes.keys()))

        for key, value in expected_attributes.iteritems():
            if value != UNIQUE_ID:
                self.assertEqual(node.get(key), value)
            else:
                self.assertIsNotNone(node.get(key))

    def test_add_xml_to_node(self):
        """
        Tests exporting block to XML
        """
        block_type = self.TestXBlock
        block = self._make_block(block_type)
        node = etree.Element(block_type.etree_node_tag)

        # precondition check
        for field_name in block.fields.keys():
            self.assertFalse(block.fields[field_name].is_set_on(block))

        block.add_xml_to_node(node)

        self._assert_node_attributes(
            node, {'force_export': 'default', 'unique_id_force_export': UNIQUE_ID}
        )

        block.field = 'Value1'
        block.simple_default = 'Value2'
        block.force_export = 'Value3'
        block.unique_id_default = 'Value4'
        block.unique_id_force_export = 'Value5'

        block.add_xml_to_node(node)

        self._assert_node_attributes(
            node,
            {
                'field': 'Value1',
                'simple_default': 'Value2',
                'force_export': 'Value3',
                'unique_id_default': 'Value4',
                'unique_id_force_export': 'Value5',
            }
        )

    @ddt.data(
        (None, {'datetime': ''}),
        (datetime(2014, 4, 1, 2, 3, 4, 567890).replace(tzinfo=pytz.utc), {'datetime': '2014-04-01T02:03:04.567890'})
    )
    @ddt.unpack
    def test_datetime_serialization(self, value, expected_attributes):
        """
        Tests exporting DateTime fields to XML
        """
        block_type = self.TestXBlockWithDateTime
        block = self._make_block(block_type)
        node = etree.Element(block_type.etree_node_tag)

        block.datetime = value

        block.add_xml_to_node(node)

        self._assert_node_attributes(node, expected_attributes)
