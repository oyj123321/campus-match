import unittest

from models import User
from match_pool import degree_compatible


def person(level=None, accept=None, cross=False):
    u = User(education_level=level, allow_cross_degree=cross)
    if accept is not None:
        u.set_accepted_degrees(accept)
    return u


class DegreePrefTests(unittest.TestCase):
    def test_same_level_matches(self):
        a, b = person("bachelor"), person("bachelor")
        self.assertTrue(degree_compatible(a, b))

    def test_default_does_not_cross(self):
        a, b = person("bachelor"), person("master")
        self.assertEqual(a.accepted_degree_list(), ["bachelor"])
        self.assertFalse(degree_compatible(a, b))

    def test_one_sided_lower_degree_does_not_match(self):
        bachelor = person("bachelor", ["bachelor", "master"])
        master = person("master", ["master"])
        self.assertFalse(degree_compatible(bachelor, master))

    def test_mutual_asymmetric_ranges_match(self):
        bachelor = person("bachelor", ["master"])
        master = person("master", ["bachelor", "master"])
        self.assertTrue(degree_compatible(bachelor, master))

    def test_legacy_cross_flag_accepts_all(self):
        a = person("bachelor", cross=True)
        b = person("doctorate", cross=True)
        self.assertEqual(a.accepted_degree_list(), ["bachelor", "master", "doctorate"])
        self.assertTrue(degree_compatible(a, b))

    def test_unknown_only_matches_someone_open_to_all(self):
        unknown = person(None)
        narrow = person("master", ["master"])
        wide = person("bachelor", ["bachelor", "master", "doctorate"])
        self.assertFalse(degree_compatible(unknown, narrow))
        self.assertTrue(degree_compatible(unknown, wide))
        self.assertTrue(degree_compatible(person(None), person(None)))

    def test_empty_selection_rejected(self):
        u = person("bachelor")
        self.assertFalse(u.set_accepted_degrees([]))
        self.assertFalse(u.set_accepted_degrees(["nope"]))


if __name__ == "__main__":
    unittest.main()
