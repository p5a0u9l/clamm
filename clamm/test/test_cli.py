""" test module for clamm.py
"""

import unittest

from clamm import cli


class TestCli(unittest.TestCase):
    """ TestCli """
    def test_config_show(self):
        """ test_tags_show """
        cli.config_show("")

    def test_tags_show(self):
        """ test_tags_show """
        cli.tags_show("")


if __name__ == "__main__":
    unittest.main()
