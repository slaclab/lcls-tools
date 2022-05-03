import unittest
from image_processing_test import ImageProcessingTest
from image_test import ImageTest
from mat_image_test import MatImageTest

loader = unittest.TestLoader()
suite = unittest.TestSuite()

suite.addTests(loader.loadTestsFromTestCase(ImageProcessingTest))
suite.addTests(loader.loadTestsFromTestCase(ImageTest))
suite.addTests(loader.loadTestsFromTestCase(MatImageTest))

runner = unittest.TextTestRunner()
result = runner.run(suite)
