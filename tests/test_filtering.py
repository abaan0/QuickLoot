import unittest

from quickloot.filtering import classify, fingerprint


class DealFilterTests(unittest.TestCase):
    def assert_category(self, message, expected):
        self.assertEqual(classify(message).category, expected, message)

    def test_food_icecream(self):
        self.assert_category("Swiggy Instamart: Amul Cake Magic Golden Fantasy icecream cake ₹54 83% OFF", "Food & snacks")

    def test_food_brownie(self):
        self.assert_category("Swiggy Instamart Loot: Brownie Circles White Chocolate for ₹16", "Food & snacks")

    def test_food_voucher(self):
        self.assert_category("Swiggy: Get Flat ₹160 off on Order Above ₹199, Code FLASHSALE", "Food delivery")

    def test_grocery_oats(self):
        self.assert_category("Swiggy Instamart Loot: Search Quaker Oats", "Groceries")

    def test_grocery_coupon(self):
        self.assert_category("BigBasket coupon: Flat ₹150 off on orders above ₹249", "Groceries")

    def test_household_detergent(self):
        self.assert_category("Zepto: Surf Excel Detergent 1kg at ₹99", "Household essentials")

    def test_household_toothpaste(self):
        self.assert_category("Blinkit: Colgate toothpaste for ₹30", "Household essentials")

    def test_airfryer_rejected_even_on_instamart(self):
        self.assert_category("Swiggy Instamart Loot: Air Fryer for ₹1", None)

    def test_washing_machine_rejected(self):
        self.assert_category("Washing machine huge 70% OFF", None)

    def test_phone_rejected(self):
        self.assert_category("BigBasket iPhone ₹9999", None)

    def test_unidentified_instamart_rejected(self):
        self.assert_category("Swiggy Instamart Loot: Search new arrivals", None)

    def test_sold_out_rejected(self):
        self.assert_category("Amul ice cream cake sold out at ₹54", None)

    def test_non_offer_rejected(self):
        self.assert_category("Today's recipe: make oats for breakfast", None)

    def test_other_city_only_rejected(self):
        self.assert_category("Noice chips ₹2 only in Bengaluru", None)

    def test_check_yours_not_rejected(self):
        self.assert_category("Noice chips ₹2 available in Bengaluru, check yours", "Food & snacks")

    def test_movie_food_coupon_rejected(self):
        self.assert_category("Movie tickets ₹150 and get 300 OFF food", None)

    def test_fingerprint_removes_link(self):
        a = fingerprint("Amul Cake ₹54 https://example.com/a")
        b = fingerprint("Amul Cake ₹54 https://example.com/b")
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
