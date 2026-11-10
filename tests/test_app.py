import unittest

from app import create_app

REF1 = dict(vcc=12, r1=47000, r2=10000, rc=4700, re=1000, beta=150, vbe=0.7)


class TestPages(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_renders_form_defaults(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        for field in (b'name="vcc"', b'name="r1"', b'name="r2"',
                      b'name="rc"', b'name="re"', b'name="beta"', b'name="vbe"'):
            self.assertIn(field, resp.data)
        self.assertIn(b"47000", resp.data)

    def test_get_renders_circuit_diagram(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'class="schematic"', resp.data)
        self.assertIn(b'aria-labelledby="schematic-title"', resp.data)
        self.assertIn(b">Q1</text>", resp.data)

    def test_post_reference_vector(self):
        resp = self.client.post("/", data=REF1)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"ACTIVE", resp.data)
        self.assertIn(b"1.324", resp.data)
        self.assertIn(b"mA", resp.data)
        self.assertIn(b"4.446", resp.data)
        self.assertIn(b"PASS", resp.data)

    def test_post_non_numeric_or_empty_is_inline_error(self):
        for bad in ("abc", ""):
            with self.subTest(value=bad):
                resp = self.client.post("/", data=dict(REF1, vcc=bad))
                self.assertEqual(resp.status_code, 200)
                self.assertIn(b"number", resp.data)
                self.assertNotIn(b"Traceback", resp.data)

    def test_post_invalid_vbe_is_inline_error(self):
        resp = self.client.post("/", data=dict(REF1, vbe="12"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"VBE", resp.data)

    def test_post_cutoff_warning(self):
        data = dict(vcc=12, r1=100000, r2=1000, rc=4700, re=1000,
                    beta=100, vbe=0.7)
        resp = self.client.post("/", data=data)
        self.assertIn(b"cut off", resp.data)


if __name__ == "__main__":
    unittest.main()
