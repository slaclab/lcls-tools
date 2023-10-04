from lcls_tools.common.data_analysis.fitting import fit_gaussian
import unittest


class TestFitGaussian(unittest.TestCase):
    
    def setUp(self) -> None:
        """ Add objects that you want to use/setup per-test-case"""
        return super().setUp()

    def tearDown(self) -> None:
        """ Add instructions for removing objects after each test case"""
        return super().tearDown()
    
    def test_get_bucket_returns_nine_if_value_over_step_equal_to_ten(self):
        """ Checks that 9 is returned if the value/step greater than or equal to 10."""
        result = fit_gaussian.get_bucket(10, 1)
        self.assertIsInstance(result, int)
        self.assertEqual(result, 9)
    
    def test_get_bucket_returns_bucket_if_value_over_step_less_than_ten(self):
        """ Checks that val/step is returned if the value/step less than 10."""
        result = fit_gaussian.get_bucket(10, 2)
        self.assertIsInstance(result, int)
        self.assertEqual(result, 5)
    
    def test_get_bucket_returns_floor_of_value_over_step_when_less_than_10(self):
        result = fit_gaussian.get_bucket(9.9, 1.5)
        self.assertIsInstance(result, int)
        self.assertEqual(result, 6)
