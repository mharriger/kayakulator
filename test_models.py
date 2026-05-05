"""
Tests for KayakModel, StringerModel, ChineMode, KeelModel, and DeckridgeModel

These tests verify that the model classes can load and process offset data.
Some tests may fail if classes are not fully implemented yet.
"""

import unittest
import os
import sys

# Add src directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from modeling.kayak_model import KayakModel
from modeling.stringer_model import StringerModel
from modeling.chine_model import ChineModel
from modeling.keel_model import KeelModel
from modeling.deckridge_model import DeckridgeModel
from offsets.json_offset_loader import load_offset_file
from offsets.member import KEEL, GUNWALE, DECKRIDGE

from OCC.Core.TopoDS import TopoDS_Wire

class TestOffsetDataLoading(unittest.TestCase):
    """Verify that test data loads correctly"""
    
    @classmethod
    def setUpClass(cls):
        """Load test data once for all tests"""
        test_data_path = os.path.join(os.path.dirname(__file__), 'data', 'SeaRoverST.offsets.json')
        cls.offset_table = load_offset_file(test_data_path)
    
    def test_offset_table_loads(self):
        """Test that SeaRoverST.offsets.json loads successfully"""
        self.assertIsNotNone(self.offset_table)
    
    def test_offset_table_has_members(self):
        """Test that offset table contains member data"""
        members = self.offset_table.members
        self.assertGreater(len(members), 0)
    
    def test_gunwale_data_available(self):
        """Test that gunwale coordinate data can be retrieved"""
        gunwale_coords = self.offset_table.get_member_coordinates(GUNWALE, ['x', 'y', 'z'])
        self.assertGreater(len(gunwale_coords), 0)
        
        # Each coordinate should be a 3-tuple (x, y, z)
        for coord in gunwale_coords:
            self.assertEqual(len(coord), 3)
    
    def test_keel_data_available(self):
        """Test that keel coordinate data can be retrieved"""
        keel_coords = self.offset_table.get_member_coordinates(KEEL, ['x', 'y', 'z'])
        self.assertGreater(len(keel_coords), 0)
    
    def test_chine_count(self):
        """Test that chine count can be determined"""
        chine_count = self.offset_table.chine_count
        self.assertGreater(chine_count, 0)


class TestStringerModel(unittest.TestCase):
    """Tests for StringerModel class"""
    
    @classmethod
    def setUpClass(cls):
        """Load test data once for all tests"""
        test_data_path = os.path.join(os.path.dirname(__file__), 'data', 'SeaRoverST.offsets.json')
        cls.offset_table = load_offset_file(test_data_path)
    
    def test_stringer_model_accepts_offset_data(self):
        """Test that ChineModel accepts offset coordinates"""
        # Get gunwale coordinates from offset table
        gunwale_coords = self.offset_table.get_member_coordinates(GUNWALE, ['x', 'y', 'z'])
        
        # ChineModel should accept these coordinates without raising during init
        # (May raise an error if implementation is incomplete, which is OK)
        model = ChineModel(gunwale_coords)
        self.assertIsNotNone(model)
    
    def test_chine_model_get_endpoints(self):
        """Test that ChineModel can return endpoints"""
        model = ChineModel(self.offset_table.get_member_coordinates(GUNWALE, ['x', 'y', 'z']))
        endpoints = model.endpoints
        # Should return a list with bow and stern endpoints
        self.assertIsNotNone(endpoints)
        self.assertEqual(len(endpoints), 2)


class TestKeelModel(unittest.TestCase):
    """Tests for KeelModel class"""
    
    @classmethod
    def setUpClass(cls):
        """Load test data once for all tests"""
        test_data_path = os.path.join(os.path.dirname(__file__), 'data', 'SeaRoverST.offsets.json')
        cls.offset_table = load_offset_file(test_data_path)
    
    def test_keel_model_instantiation(self):
        """Test that KeelModel can be instantiated"""
        keel_coords = self.offset_table.get_member_coordinates(KEEL, ['x', 'y', 'z'])
        
        # Create dummy endpoints
        bow_endpoint = (20, 0)
        stern_endpoint = (1000, 10)
        gunwale_bow = (0, 100)
        gunwale_stern = (1000, 50)
        
        # KeelModel should be instantiable
        model = KeelModel(keel_coords, bow_endpoint, stern_endpoint, gunwale_bow, gunwale_stern)
        self.assertIsNotNone(model)

class TestDeckridgeModel(unittest.TestCase):
    """Tests for DeckridgeModel class"""
    
    @classmethod
    def setUpClass(cls):
        """Load test data once for all tests"""
        test_data_path = os.path.join(os.path.dirname(__file__), 'data', 'SeaRoverST.offsets.json')
        cls.offset_table = load_offset_file(test_data_path)
    
    def test_deckridge_model_instantiation(self):
        """Test that DeckridgeModel can be instantiated"""
        # Use default coordinates (x, z) like the actual usage in kayak_model.py
        deckridge_coords = self.offset_table.get_member_coordinates(DECKRIDGE, ['x', 'y', 'z'])
        
        # Create dummy gunwale endpoints as 2D tuples (y, z)
        gunwale_bow = (0, 100)
        gunwale_stern = (1000, 100)
        
        # DeckridgeModel should be instantiable
        model = DeckridgeModel(deckridge_coords, gunwale_bow, gunwale_stern)
        self.assertIsNotNone(model)

class TestKayakModel(unittest.TestCase):
    """Tests for KayakModel class"""
    
    @classmethod
    def setUpClass(cls):
        """Load test data once for all tests"""
        test_data_path = os.path.join(os.path.dirname(__file__), 'data', 'SeaRoverST.offsets.json')
        cls.offset_table = load_offset_file(test_data_path)
    
    def test_kayak_model_has_required_attributes(self):
        """Test that KayakModel has required attributes after empty init"""
        model = KayakModel(self.offset_table)
        self.assertTrue(hasattr(model, '_gunwale'))
        self.assertTrue(hasattr(model, '_chines'))
        self.assertTrue(hasattr(model, '_keel'))
        self.assertTrue(hasattr(model, '_deckridge'))

    def test_kayak_model_initialization_with_offset_table(self):
        """Test that KayakModel can be initialized with an offset table"""
        model = KayakModel(self.offset_table)
        self.assertIsNotNone(model)
    
    def test_kayak_model_chines_is_list(self):
        """Test that KayakModel's chines is a list"""
        model = KayakModel(self.offset_table)
        self.assertIsInstance(model._chines, list)
    
    def test_kayak_model_keel_is_keel_model(self):
        """Test that KayakModel's keel is a KeelModel"""
        model = KayakModel(self.offset_table)
        self.assertIsInstance(model._keel, KeelModel)

    
    def test_kayak_model_deckridge_is_deckridge_model(self):
        """Test that KayakModel's deckridge is a DeckridgeModel"""
        model = KayakModel(self.offset_table)
        self.assertIsInstance(model._deckridge, DeckridgeModel)
   
    def test_kayak_model_all_members_complete(self):
        model = KayakModel(self.offset_table)
        self.assertTrue(model._gunwale.modeling_complete)
        self.assertTrue(all((c.modeling_complete for c in model._chines)))
        self.assertTrue(model._keel.modeling_complete)
        self.assertTrue(model._deckridge.modeling_complete)

    def test_kayak_model_all_members_have_wires(self):
        model = KayakModel(self.offset_table)
        self.assertTrue(all(isinstance(w, TopoDS_Wire) for w in model._gunwale.wires))
        self.assertTrue(all(isinstance(w, TopoDS_Wire) for w in model._keel.wires))
        self.assertTrue(all(isinstance(w, TopoDS_Wire) for w in model._deckridge.wires))
        self.assertTrue((all((isinstance(w, TopoDS_Wire) for w in c.wires) for c in model._chines)))

if __name__ == '__main__':
    unittest.main()
