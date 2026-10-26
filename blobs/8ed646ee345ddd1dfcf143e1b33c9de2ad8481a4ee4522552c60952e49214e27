#!/usr/bin/env python3
import copy
import unittest
from audit_upload_startup import audit_scene_components

class ComponentSlots(unittest.TestCase):
    def fixture(self):
        return [1, 0, [], [["cc.Node", ["_name", "_components"], 0, 2]],
                [[0, 0, 1, 1]], [[0, "Canvas", [[[1, "valid-component"], None], 4, 0]]]]
    def test_corrupted_compiled_slot(self):
        self.assertTrue(audit_scene_components(self.fixture(), "subpackages/main/import/a.json"))
    def test_direct_typed_component_array(self):
        data = self.fixture(); data[5][0][2] = [[1, "valid-component"], None]
        self.assertTrue(audit_scene_components(data, "scene.json"))
    def test_valid_components(self):
        data = self.fixture(); data[5][0][2][0].pop()
        self.assertEqual([], audit_scene_components(data, "assets/main/import/a.json"))
    def test_optional_null_is_not_component_failure(self):
        self.assertEqual([], audit_scene_components([{"__type__":"cc.Node", "_components":[], "_prefab":None}], "scene.json"))
    def test_uncompressed_null_slot(self):
        self.assertTrue(audit_scene_components([{"__type__":"cc.Node", "_components":[None]}], "scene.json"))
if __name__ == "__main__": unittest.main()
