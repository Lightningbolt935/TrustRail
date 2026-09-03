"""
Catalog Service
Provides search, filter, and detail lookup for products.
"""
from typing import List, Optional
from backend.catalog.models import Product
from backend.catalog.seed_data import SEED_PRODUCTS, PRODUCT_LOOKUP


class CatalogService:
    def __init__(self, products: Optional[List[Product]] = None):
        self._products = products if products is not None else list(SEED_PRODUCTS)
        self._lookup = {p.id: p for p in self._products}

    def list_products(self, category: Optional[str] = None, max_price: Optional[float] = None) -> List[Product]:
        """List products with optional category and max_price filtering."""
        results = []
        for p in self._products:
            if category and category.lower() != "all" and p.category.lower() != category.lower():
                continue
            if max_price is not None and p.price > max_price:
                continue
            results.append(p)
        return results

    def get_product(self, product_id: str) -> Optional[Product]:
        """Lookup single product by ID."""
        return self._lookup.get(product_id)

    def add_product(self, product: Product) -> Product:
        """Add product to catalog."""
        self._products.append(product)
        self._lookup[product.id] = product
        return product


# Global singleton catalog service
catalog_service = CatalogService()
