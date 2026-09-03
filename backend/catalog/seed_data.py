"""
Catalog Seed Data for TrustRail Demo and Tests
"""
from typing import List, Dict
from backend.catalog.models import Product

SEED_PRODUCTS: List[Product] = [
    # Essentials (Permitted in Bronze, Silver, Gold)
    Product(
        id="prod_ess_001",
        name="Minimalist Dot Notebook & Pen",
        category="essentials",
        price=249.0,
        currency="INR",
        description="Premium 120 GSM dotted journal with archival ink gel pen.",
        image_emoji="📓",
    ),
    Product(
        id="prod_ess_002",
        name="Organic Darjeeling Green Tea (100g)",
        category="essentials",
        price=399.0,
        currency="INR",
        description="Single-estate organic whole-leaf Himalayan green tea.",
        image_emoji="🍵",
    ),
    Product(
        id="prod_ess_003",
        name="Braided USB-C Fast Charge Cable (1.5m)",
        category="essentials",
        price=450.0,
        currency="INR",
        description="Durable 60W power delivery braided nylon cord.",
        image_emoji="🔌",
    ),

    # Apparel (Permitted in Silver, Gold - Blocked in Bronze)
    Product(
        id="prod_app_001",
        name="Blue Cotton Crewneck T-Shirt",
        category="apparel",
        price=799.0,
        currency="INR",
        description="100% combed ringspun cotton, breathable slim-fit tee.",
        image_emoji="👕",
    ),
    Product(
        id="prod_app_002",
        name="Lightweight Breathable Running Shoes",
        category="apparel",
        price=1899.0,
        currency="INR",
        description="Shock-absorbing responsive sole engineered for daily running.",
        image_emoji="👟",
    ),
    Product(
        id="prod_app_003",
        name="Heavyweight Indigo Denim Jacket",
        category="apparel",
        price=2499.0,
        currency="INR",
        description="Classic vintage washed denim jacket. Exceeds Silver per-txn cap!",
        image_emoji="🧥",
    ),

    # Electronics (Permitted in Silver, Gold - Blocked in Bronze)
    Product(
        id="prod_elec_001",
        name="Ergonomic Wireless Silent Mouse",
        category="electronics",
        price=899.0,
        currency="INR",
        description="2.4GHz + Bluetooth dual mode ergonomic palm grip mouse.",
        image_emoji="🖱️",
    ),
    Product(
        id="prod_elec_002",
        name="Compact Mechanical Keyboard (Tenkeyless)",
        category="electronics",
        price=1999.0,
        currency="INR",
        description="Tactile brown switches with customizable white backlight.",
        image_emoji="⌨️",
    ),
    Product(
        id="prod_elec_003",
        name="ANC Noise-Cancelling Wireless Headphones",
        category="electronics",
        price=5999.0,
        currency="INR",
        description="Active hybrid noise cancellation with 40-hour playback. Requires Gold!",
        image_emoji="🎧",
    ),

    # Luxury (Permitted ONLY in Gold - Blocked in Bronze & Silver)
    Product(
        id="prod_lux_001",
        name="Titanium Smartwatch Pro Sapphire",
        category="luxury",
        price=8999.0,
        currency="INR",
        description="Aerospace-grade titanium casing, AMOLED display, ECG monitor.",
        image_emoji="⌚",
    ),
    Product(
        id="prod_lux_002",
        name="Full-Grain Italian Leather Weekender Bag",
        category="luxury",
        price=12500.0,
        currency="INR",
        description="Handcrafted vegetable-tanned leather travel bag. Exceeds Gold single-txn!",
        image_emoji="🧳",
    ),

    # Failure Simulator Product (Deliberately triggers simulated gateway timeout)
    Product(
        id="prod_fail_timeout",
        name="Simulated Gateway Timeout Dongle",
        category="essentials",
        price=499.13,
        currency="INR",
        description="Special test SKU (ends in .13) engineered to trigger simulated Razorpay gateway timeout.",
        image_emoji="⚠️",
    ),
]

PRODUCT_LOOKUP: Dict[str, Product] = {p.id: p for p in SEED_PRODUCTS}
