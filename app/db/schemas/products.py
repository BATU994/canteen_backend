from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class ProductBase(BaseModel):
    id:int
    name: str
    quantity: int
    reg_time: datetime
    price: int
    prod_type: str
    image_path: str | None = None

class ProductBasePatch(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = None
    reg_time: Optional[datetime] = None
    price:Optional[int] = None
    prod_type:Optional[str] = None
    image_path:Optional[str] = None