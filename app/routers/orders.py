from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Set, Dict
import random
from app.db.models import Users, Products
from app.db.sessions import get_async_session, async_session_maker
from app.db.models import Order as OrderModel
from app.db.schemas.orders import OrderSend, Order, OrderItem, OrderUpdate

router = APIRouter(prefix="/order", tags=["order"])

# ============================================================
#   ACTIVE WEBSOCKET CONNECTIONS STORAGE
# ============================================================
active_connections: Set[WebSocket] = set()
# Store WebSocket connections per user_id
user_connections: Dict[int, Set[WebSocket]] = {}


async def broadcast_order(order: OrderModel, message_type: str = "order_update"):
    """Send order updates to all WebSocket subscribers"""
    message = {
        "type": message_type,
        "data": {
            "id": order.id,
            "user_id": order.user_id,
            "user_name": order.user_name,
            "code": order.code,
            "items": order.items,
            "price": order.price,
            "comment": order.comment,
            "status": order.status,
            "timestamp": order.timestamp.isoformat()
        }
    }

    dead = []
    for ws in active_connections:
        try:
            await ws.send_json(message)
        except:
            dead.append(ws)

    for ws in dead:
        active_connections.remove(ws)


async def broadcast_to_user(user_id: int, order_id: int, status: str):
    """Send order status update to specific user's WebSocket connections"""
    if user_id not in user_connections:
        return
    
    # 🔥 FIXED: Added proper type segregation
    message = {
        "type": "status_changed",  # Clear type for status updates
        "order_id": order_id,
        "status": status
    }
    
    dead = []
    for ws in user_connections[user_id]:
        try:
            await ws.send_json(message)
        except:
            dead.append(ws)
    
    # Clean up dead connections
    for ws in dead:
        user_connections[user_id].discard(ws)
    
    # Remove empty sets
    if not user_connections[user_id]:
        del user_connections[user_id]


@router.post("/broadcast")
async def broadcast_order_update(
    db: AsyncSession = Depends(get_async_session)
):
    """Broadcast all orders to WebSocket clients"""

    result = await db.execute(select(OrderModel))
    orders = result.scalars().all()

    if not orders:
        raise HTTPException(status_code=404, detail="No orders found")

    # Convert to serializable dicts
    orders_json = [order.to_dict() for order in orders]

    await broadcast_order(orders_json)
    return {"status": "broadcast_sent"}



# ============================================================
#  UNIQUE ORDER CODE GENERATOR
# ============================================================
async def generate_unique_code(session: AsyncSession) -> str:
    allowed_letters = [
        '1','2','3','4','5','6','7','8','9'
    ]

    while True:
        code = ''.join(random.choice(allowed_letters) for _ in range(3))

        result = await session.execute(
            select(OrderModel).filter(OrderModel.code == code)
        )
        exists = result.scalar_one_or_none()

        if not exists:
            return code


# ============================================================
#  GET ORDERS
# ============================================================
@router.get("/all", response_model=list[Order])
async def get_all_orders(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(OrderModel).where(OrderModel.status.not_in(["paid", "cancelled"])))
    return result.scalars().all()


@router.get("/{user_id}", response_model=list[Order])
async def get_user_orders(user_id: int, db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(
        select(OrderModel).where(OrderModel.user_id == user_id).order_by(OrderModel.timestamp.asc())
    )
    return result.scalars().all()


# ============================================================
#  DELETE ORDER
# ============================================================
@router.delete("/delete/{order_id}")
async def delete_order(order_id: int, db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(OrderModel).where(OrderModel.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    await db.delete(order)
    await db.commit()

    return {"message": "Order deleted successfully"}


# ============================================================
#  POST — CREATE ORDER
# ============================================================
@router.post("/create", response_model=Order)
async def create_order(
    order: OrderSend,
    session: AsyncSession = Depends(get_async_session)
):
    # 1️⃣ Get user from DB
    result = await session.execute(
        select(Users).where(Users.id == order.user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # 2️⃣ Generate order code
    code = await generate_unique_code(session)

    # 3️⃣ Check and update product quantities
    for item in order.items:
        # Get the product
        product_result = await session.execute(
            select(Products).where(Products.id == item.product_id)
        )
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product with id {item.product_id} not found"
            )
            
        if product.quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough quantity for product {product.name}. Available: {product.quantity}, Requested: {item.quantity}"
            )
            
        # Update the quantity
        product.quantity -= item.quantity

    # 4️⃣ Create order
    new_order = OrderModel(
        user_id=order.user_id,
        user_name=user.name,
        code=code,
        items=[item.dict() for item in order.items],
        price=order.price,
        comment=order.comment,
        status="pending",
    )

    session.add(new_order)
    
    try:
        await session.commit()
        await session.refresh(new_order)
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error creating order: {str(e)}"
        )

    # 5️⃣ Broadcast to websocket listeners
    await broadcast_order(new_order, message_type="order_created")

    return new_order



# ============================================================
#  UPDATE ORDER STATUS
# ============================================================
@router.patch("/{order_id}", response_model=Order)
async def update_order_status(
    order_id: int, 
    update_data: OrderUpdate,
    db: AsyncSession = Depends(get_async_session)
):
    """Update the status of an order and broadcast to user's WebSocket"""
    # Get the order
    result = await db.execute(
        select(OrderModel).where(OrderModel.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Update status
    order.status = update_data.status
    
    try:
        await db.commit()
        await db.refresh(order)
        
        # 🔔 Broadcast to the specific user's WebSocket connections
        await broadcast_to_user(
            user_id=order.user_id,
            order_id=order.id,
            status=order.status
        )
        
        return order
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error updating order: {str(e)}")

# ============================================================
#  WEBSOCKET — RECEIVE REAL-TIME ORDER UPDATES
# ============================================================
@router.websocket("/ws")
async def orders_websocket(websocket: WebSocket):
    """
    General WebSocket endpoint for real-time order updates.
    Clients will receive messages with full order data.
    
    Message types:
    - connection_established: Initial connection confirmation
    - order_created: New order created
    - order_update: Order data updated
    - pong: Response to ping
    """
    await websocket.accept()
    active_connections.add(websocket)
    
    try:
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to order updates"
        })
        
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    finally:
        active_connections.discard(websocket)
@router.websocket("/ws/updates/{user_id}")
async def user_order_updates_websocket(websocket: WebSocket, user_id: int):
    """
    User-specific WebSocket endpoint for order status updates.
    
    Message types sent to client:
    1. connection_established: When connection is first established
       {
           "type": "connection_established",
           "message": "Connected to order updates for user {user_id}",
           "user_id": int
       }
    
    2. status_changed: When order status is updated
       {
           "type": "status_changed",
           "order_id": int,
           "status": str
       }
    
    3. pong: Response to client ping
       {
           "type": "pong"
       }
    """
    await websocket.accept()
    if user_id not in user_connections:
        user_connections[user_id] = set()
    user_connections[user_id].add(websocket)
    
    try:
        await websocket.send_json({
            "type": "connection_established",
            "message": f"Connected to order updates for user {user_id}",
            "user_id": user_id
        })
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("action") == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {str(e)}")
    finally:
        if user_id in user_connections:
            user_connections[user_id].discard(websocket)
            if not user_connections[user_id]:
                del user_connections[user_id]   