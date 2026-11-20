"""Product-first classification. A store name alone is never sufficient."""

import hashlib
import re
from dataclasses import dataclass

# Everyday consumables rather than appliances or all shopping categories.
FOOD = (
    "cake", "ice cream", "icecream", "kulfi", "brownie", "chocolate", "cocoa",
    "biscuit", "cookie", "chips", "nachos", "namkeen", "snack", "wafer", "popcorn",
    "candy", "sweet", "mithai", "laddu", "ladoo", "barfi", "rasgulla",
    "pastry", "bakery", "bread", "bun", "donut", "croissant", "pizza",
    "burger", "biryani", "momos", "roll", "sandwich", "pasta", "noodles",
    "maggi", "samosa", "fries", "dessert", "pudding", "yogurt", "yoghurt",
    "curd", "paneer", "cheese", "butter", "milk", "milkshake", "lassi",
    "juice", "soft drink", "soda", "cola", "coffee", "tea", "energy drink",
    "protein bar", "granola bar", "energy bar", "icecream cake", "noice",
    "fruit juice", "breakfast cereal", "cornflakes", "corn flakes",
    "dry fruit", "cashew", "almond", "pistachio", "peanut", "cranberry"
)
GROCERIES = (
    "rice", "atta", "flour", "maida", "besan", "dal", "daal", "lentil",
    "pulses", "rajma", "chana", "chickpea", "cooking oil", "mustard oil",
    "sunflower oil", "groundnut oil", "olive oil", "refined oil", "ghee",
    "sugar", "salt", "spice", "masala", "turmeric", "haldi", "chilli",
    "chili", "oats", "quaker", "vegetable", "fruit", "apple", "banana",
    "mango", "onion", "tomato", "potato", "garlic", "ginger", "egg", "eggs",
    "chicken", "fish", "meat", "bread", "milk", "curd", "paneer",
    "honey", "jam", "pickle", "sauce", "ketchup", "noodles", "pasta",
    "chocolate spread", "peanut butter", "chyawanprash", "aashirvaad"
)
HOUSEHOLD = (
    "detergent", "washing powder", "washing liquid", "fabric softener",
    "dishwash", "dish wash", "dishwashing", "soap", "handwash", "hand wash",
    "body wash", "shampoo", "conditioner", "toothpaste", "toothbrush",
    "mouthwash", "face wash", "sanitizer", "sanitiser", "disinfectant",
    "floor cleaner", "toilet cleaner", "surface cleaner", "phenyl",
    "garbage bag", "trash bag", "tissue", "toilet paper", "paper towel",
    "wet wipes", "baby wipes", "diaper", "sanitary pad", "period pad",
    "laundry", "cleaning spray", "scrub pad", "sponge", "mosquito repellent",
    "insect repellent", "air freshener", "deodorant", "shaving cream",
    "razor", "cotton buds", "napkin"
)
# These always win, even when the post says "Swiggy Instamart Loot".
BLOCKED_PRODUCTS = (
    "washing machine", "refrigerator", "fridge", "air fryer", "airfryer",
    "microwave oven", "oven", "induction cooktop", "cooktop", "gas stove",
    "mixer grinder", "grinder", "blender", "juicer machine", "dishwasher",
    "television", "smart tv", "led tv", "laptop", "computer", "keyboard",
    "mouse", "monitor", "smartphone", "iphone", "android phone", "tablet",
    "headphone", "earphone", "earbuds", "power bank", "charger",
    "smartwatch", "smart watch", "camera", "speaker", "printer",
    "vacuum cleaner", "robot vacuum", "ceiling fan", "air cooler",
    "air conditioner", "ac 1.5 ton", "water heater", "geyser",
    "furniture", "mattress", "sofa", "wardrobe", "curtain", "bedsheet",
    "bedsheets", "bed sheet", "shoe", "sneaker", "jeans", "trouser",
    "shirt", "t-shirt", "tshirt", "jacket", "saree", "kurta", "handbag",
    "backpack", "luggage", "suitcase", "gold coin", "silver coin",
    "jewellery", "jewelry", "necklace", "perfume", "makeup", "lipstick",
    "spectacles", "eyeglasses", "sunglasses", "movie ticket", "movie tickets",
    "gift card", "recharge", "mobile data", "upi cashback", "credit card",
    "debit card", "insurance", "flight ticket", "hotel booking"
)
FOOD_DELIVERY = ("swiggy", "zomato", "eatsure", "domino", "pizza hut")
GROCERY_PLATFORMS = (
    "instamart", "blinkit", "zepto", "bigbasket", "big basket", "jiomart",
    "jio mart", "dmart", "amazon fresh", "flipkart minutes"
)
DEAL_PHRASES = (
    "loot", "offer", "deal", "discount", "coupon", "promo code", "use code",
    "apply code", "flat", "off", "free", "bogo", "buy one get one", "lowest",
    "price drop", "price error", "mrp error", "cashback", "search :", "search:"
)


def _contains(text: str, phrases: tuple[str, ...]) -> bool:
    return any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text) for term in phrases)


def fingerprint(text: str) -> str:
    """Deduplicate identical reposted offers, including across channels."""
    text = re.sub(r"https?://\S+", "", text.lower())
    text = re.sub(r"[^\w₹%]+", " ", text, flags=re.UNICODE).strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True)
class Classification:
    category: str | None
    reason: str


def classify(text: str, preferred_city: str = "Mumbai") -> Classification:
    t = re.sub(r"\s+", " ", text.casefold()).strip()

    if not t:
        return Classification(None, "empty")
    if _contains(t, ("sold out", "expired", "deal over", "offer ended", "out of stock")):
        return Classification(None, "unavailable or expired")
    if _contains(t, BLOCKED_PRODUCTS):
        return Classification(None, "excluded non-consumable product")

    # Skip posts explicitly exclusive to another city. "Check yours" is not
    # treated as an exclusive claim because availability might vary by PIN.
    other_cities = ("bengaluru", "bangalore", "delhi", "hyderabad", "pune", "chennai", "kolkata", "ahmedabad")
    if preferred_city:
        for city in other_cities:
            if city != preferred_city.casefold() and re.search(
                rf"\b(?:only|exclusively|exclusive)\s+(?:in|for|at)\s+{re.escape(city)}\b|\bonly\s+{re.escape(city)}\b",
                t,
            ):
                return Classification(None, f"only available in {city}")

    has_price = bool(re.search(r"(?:₹|rs\.?\s*)\s*[\d,]+|\b\d+(?:\.\d+)?\s*%\s*off\b", t))
    has_deal = has_price or _contains(t, DEAL_PHRASES)
    if not has_deal:
        return Classification(None, "no offer signal")

    if _contains(t, FOOD):
        return Classification("Food & snacks", "food item")
    if _contains(t, GROCERIES):
        return Classification("Groceries", "grocery item")
    if _contains(t, HOUSEHOLD):
        return Classification("Household essentials", "daily-use household item")

    # Only restaurant/order-wide offers, not all products on Swiggy.
    if _contains(t, FOOD_DELIVERY) and not _contains(t, ("instamart",)):
        if _contains(t, ("food", "restaurant", "order", "meal", "dineout", "delivery")):
            return Classification("Food delivery", "food-order offer")

    # Genuine cart-wide coupons at grocery apps qualify without item names.
    if _contains(t, GROCERY_PLATFORMS) and _contains(
        t, ("cart", "order above", "minimum order", "entire order", "all groceries", "flat off", "coupon")
    ):
        return Classification("Groceries", "grocery cart offer")

    return Classification(None, "product not in selected categories")
