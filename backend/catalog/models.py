"""
Product and Catalog Models
"""
from pydantic import BaseModel, Field
from typing import Optional


class Product(BaseModel):
    id: str
    name: str
    category: str
    price: float = Field(..., description="Price in INR")
    currency: str = "INR"
    description: str = ""
    in_stock: bool = True
    image_emoji: str = "📦"
