import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.sql.schema import ForeignKey
from .sessions import Base
from uuid import uuid4
from sqlalchemy import Enum

class Order(Base):
    __tablename__ = "orders"
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"), nullable=False)
    items = sa.Column(sa.JSON, nullable=False)
    comment = sa.Column(sa.Text, nullable= True)
    timestamp = sa.Column(sa.DateTime, server_default=sa.func.now(), nullable=False)
    code = sa.Column(sa.Text , nullable=False, unique= True)
    price = sa.Column(sa.Integer, nullable= False)
    is_active = sa.Column(sa.Boolean, nullable = False, default=True)
    user_name = sa.Column(sa.Text, nullable = True, default=True)
    status = sa.Column(
    Enum(
        "cancelled",
        "pending",
        "ready",
        "paid",
        name="order_status_enum"
    ),
    nullable=False,
    default="pending",
    server_default="pending"
    )


class Users(Base):  
    __tablename__ = "users"

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    email = sa.Column(sa.Text, nullable=False, unique=True)
    password = sa.Column(sa.Text, nullable=False)
    name = sa.Column(sa.Text, nullable=False)
    creation_date = sa.Column(sa.DateTime, server_default=sa.func.now(), nullable=False)

class Products(Base):
    __tablename__ = "products"

    id = sa.Column(sa.Integer, primary_key= True, index=True)
    name = sa.Column(sa.Text, nullable=False, unique= True)
    price = sa.Column(sa.Integer, nullable = False)
    quantity = sa.Column(sa.Integer, nullable = False)
    reg_time = sa.Column(sa.DateTime, server_default=sa.func.now(), nullable=False)
    prod_type = sa.Column(sa.Text, nullable=False) 
    image_path = sa.Column(sa.Text, nullable=True)