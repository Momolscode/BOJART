"""The oversized vendor exception is bound to one path and exact upstream bytes."""
import unittest
from tools.validate_repository import ROOT, source_size_allowed


class VendorSourcePolicyTests(unittest.TestCase):
    def test_exact_dependency_is_accepted(self):
        name='sites/atelier/dist/vendor/three.core.js'
        self.assertTrue(source_size_allowed(name,(ROOT/name).read_bytes()))

    def test_changed_vendor_is_not_exempt(self):
        name='sites/atelier/dist/vendor/three.core.js'
        raw=(ROOT/name).read_bytes()
        self.assertFalse(source_size_allowed(name,b'!'+raw[1:]))

    def test_identical_content_at_another_path_is_not_exempt(self):
        raw=(ROOT/'sites/atelier/dist/vendor/three.core.js').read_bytes()
        self.assertFalse(source_size_allowed('unreviewed.js',raw))

    def test_general_text_limit_is_unchanged(self):
        self.assertTrue(source_size_allowed('small.txt',b'a'*1_000_000))
        self.assertFalse(source_size_allowed('large.txt',b'a'*1_000_001))
