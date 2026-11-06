import unittest

from src.analysis import check_discount


class CheckDiscountTests(unittest.TestCase):
    def test_no_data(self):
        self.assertEqual(check_discount([])["verdict"], "No data")

    def test_no_sale_shown(self):
        result = check_discount([(5999, None)] * 10)
        self.assertEqual(result["verdict"], "No discount claimed")

    def test_needs_a_week_of_history(self):
        result = check_discount([(5999, 18999)] * 3)
        self.assertEqual(result["verdict"], "Not enough data")

    def test_always_on_sale_is_suspicious(self):
        result = check_discount([(5999, 18999)] * 10)
        self.assertEqual(result["verdict"], "Suspicious discount")
        self.assertEqual(result["claimed_off"], 68)
        self.assertEqual(result["real_off"], 0)

    def test_genuine_discount(self):
        result = check_discount([(10000, None)] * 8 + [(7000, 10000)])
        self.assertEqual(result["verdict"], "Genuine discount")
        self.assertEqual(result["real_off"], 30)

    def test_price_raised_before_sale(self):
        history = [(5000, None)] * 10 + [(7000, None)] * 3 + [(5000, 8000)]
        result = check_discount(history)
        self.assertEqual(result["verdict"], "Suspicious discount")
        self.assertTrue(any("went up" in reason for reason in result["reasons"]))

    def test_real_drop_but_exaggerated(self):
        result = check_discount([(6000, None)] * 8 + [(5000, 18999)])
        self.assertEqual(result["verdict"], "Real drop, exaggerated claim")


if __name__ == "__main__":
    unittest.main()