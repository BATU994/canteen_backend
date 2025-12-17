from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import sessions
from app.db.models import Products
from app.db.schemas import products as products_schema
import uuid
import shutil
import os
from datetime import datetime
from sqlalchemy.exc import IntegrityError

router = APIRouter(
    prefix="/products",
    tags=["products"]
)

UPLOAD_DIR = "app/static/products"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/post", response_model=products_schema.ProductBase)
async def create_product(
    name: str = Form(...),
    quantity: int = Form(...),
    price: float = Form(...),
    prod_type: str = Form(...),
    image: UploadFile = File(...),
    db: AsyncSession = Depends(sessions.get_async_session)
):
    extension = image.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{extension}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    db_path = f"/static/products/{filename}" 

    existing_product = await db.execute(select(Products).where(Products.name == name))
    if existing_product.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="This name is already posted")

    item = Products(
        name=name,
        quantity=quantity,
        reg_time=datetime.now(),
        price=price,
        prod_type=prod_type,
        image_path=db_path 
    )

    db.add(item)
    try:
        await db.commit()
        await db.refresh(item)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="This name is already posted")

    return item

@router.get("/", response_model=list[products_schema.ProductBase])
async def get_all_products(db: AsyncSession = Depends(sessions.get_async_session)):
    result = await db.execute(select(Products))
    return result.scalars().all()


@router.get("/one/{prod_id}", response_model=products_schema.ProductBase)
async def get_product(prod_id: str, db: AsyncSession = Depends(sessions.get_async_session)):
    result = await db.execute(select(Products).filter(Products.id == prod_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.put("/put/{prod_id}", response_model=products_schema.ProductBase)
async def update_product(
    prod_id: int,
    name: str = Form(None),
    quantity: int = Form(None),
    price: float = Form(None),
    prod_type: str = Form(None),
    image: UploadFile | None = File(None),  # file is optional
    db: AsyncSession = Depends(sessions.get_async_session),
):
    # Fetch the existing item
    result = await db.execute(select(Products).filter(Products.id == prod_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # --- Update fields if they were sent ---
    if name is not None:
        item.name = name
    if quantity is not None:
        item.quantity = quantity
    if price is not None:
        item.price = price
    if prod_type is not None:
        item.prod_type = prod_type

    # --- Update image if a new file is sent ---
    if image is not None:
        extension = image.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{extension}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        # Store URL-friendly path
        item.image_path = f"/static/products/{filename}"

    # Commit changes
    await db.commit()
    await db.refresh(item)

    return item

@router.delete("/delete/{prod_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lostandfound(prod_id: int, db: AsyncSession = Depends(sessions.get_async_session)):
    result = await db.execute(select(Products).filter(Products.id == prod_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()
    return None

@router.patch("/patch/{prod_id}", response_model=products_schema.ProductBase)
async def patch_product(
    prod_id: int,
    updates: products_schema.ProductBasePatch,
    db: AsyncSession = Depends(sessions.get_async_session),
):
    result = await db.execute(select(Products).filter(Products.id == prod_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    data = updates.model_dump(exclude_unset=True, exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields provided to update")
    for key, value in data.items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item

