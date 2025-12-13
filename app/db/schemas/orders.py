from pydantic import BaseModel
from datetime import datetime
from typing import List, Literal

class OrderItem(BaseModel):
    product_id: int
    name: str
    quantity: int
    price: int

class Order(BaseModel):
    id: int
    user_id: int
    price: int
    user_name: str
    code: str
    items: List[OrderItem]
    comment: str | None = None
    timestamp: datetime
    status: Literal["cancelled", "pending", "ready", "paid"] = "pending"


class OrderSend(BaseModel):
    user_id: int
    items: List[OrderItem]
    comment: str
    price:int


class OrderUpdate(BaseModel):
    status: Literal["cancelled", "pending", "ready", "paid"] = "pending"