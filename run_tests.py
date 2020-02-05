import unittest
from image_processing_test import ImageProcessingTest

loader = unittest.TestLoader()
suite = unittest.TestSuite()

suite.addTests(loader.loadTestsFromTestCase(ImageProcessingTest))

runner = unittest.TextTestRunner()
result = runner.run(suite)

#def create_suite():
#    test_suite = unittest.TestSuite()
#    test_suite.addTest(ImageProcessingTest())
#    return test_suite

#if __name__ == '__main__':
#    suite = create_suite()
#    runner = unittest.TextTestRunner()
#    runner.run(suite)
