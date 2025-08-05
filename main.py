from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List
import xmlrpc.client

app = FastAPI()

# Odoo connection config
url = "http://localhost:8069"
db = "hackathon_db"
username = "vinya.k@thesmatwork.com"
password = "admin"

# Connect and authenticate with Odoo
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, username, password, {})
if not uid:
    raise Exception("Failed to authenticate with Odoo")

models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

# --- Pydantic models ---

class Event(BaseModel):
    name: str
    date_begin: str
    date_end: str

class OrderLineItem(BaseModel):
    product_id: int
    product_uom_qty: float

class SaleOrderInput(BaseModel):
    partner_id: int
    date_order: str
    order_line: List[OrderLineItem]

class Product(BaseModel):
    name: str
    list_price: float

# --- Event Endpoints ---

@app.get("/odoo/events")
def get_events():
    event_ids = models.execute_kw(db, uid, password, 'event.event', 'search', [[]])
    events = models.execute_kw(db, uid, password, 'event.event', 'read', [event_ids],
                               {'fields': ['id', 'name', 'date_begin', 'date_end']})
    return {"events": events}

@app.post("/odoo/events")
def create_event(event: Event):
    event_data = {
        'name': event.name,
        'date_begin': event.date_begin,
        'date_end': event.date_end
    }
    event_id = models.execute_kw(db, uid, password, 'event.event', 'create', [event_data])
    return {"message": "Event created", "event_id": event_id}

# --- Sales Orders Endpoints ---

@app.get("/odoo/sales_orders")
def get_sales_orders():
    try:
        sales_ids = models.execute_kw(db, uid, password, 'sale.order', 'search', [[]])
        sales = models.execute_kw(db, uid, password, 'sale.order', 'read', [sales_ids],
                                  {'fields': ['id', 'name', 'partner_id', 'date_order', 'amount_total']})
        return {"sales_orders": sales}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sales orders: {str(e)}")

@app.post("/odoo/sales_orders")
def create_sales_order(order: SaleOrderInput):
    try:
        order_lines = [(0, 0, {
            'product_id': line.product_id,
            'product_uom_qty': line.product_uom_qty
        }) for line in order.order_line]

        order_data = {
            'partner_id': order.partner_id,
            'date_order': order.date_order,
            'order_line': order_lines
        }

        order_id = models.execute_kw(db, uid, password, 'sale.order', 'create', [order_data])
        return {"message": "Sale order created", "order_id": order_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create sale order: {str(e)}")

# --- Products Endpoints ---

# ✅ GET with pagination
@app.get("/odoo/products")
def get_products(skip: int = Query(0), limit: int = Query(10)):
    try:
        product_ids = models.execute_kw(db, uid, password, 'product.product', 'search', [[]],
                                        {'offset': skip, 'limit': limit})
        products = models.execute_kw(db, uid, password, 'product.product', 'read', [product_ids],
                                     {'fields': ['id', 'name', 'list_price', 'categ_id']})
        return {"products": products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ GET product by ID
@app.get("/odoo/products/{product_id}")
def get_product_by_id(product_id: int):
    try:
        product = models.execute_kw(db, uid, password, 'product.product', 'read', [[product_id]],
                                    {'fields': ['id', 'name', 'list_price', 'categ_id']})
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ GET products by category ID
@app.get("/odoo/products/category/{category_id}")
def get_products_by_category(category_id: int, skip: int = Query(0), limit: int = Query(10)):
    try:
        product_ids = models.execute_kw(db, uid, password, 'product.product', 'search',
                                        [[('categ_id', '=', category_id)]],
                                        {'offset': skip, 'limit': limit})
        products = models.execute_kw(db, uid, password, 'product.product', 'read', [product_ids],
                                     {'fields': ['id', 'name', 'list_price', 'categ_id']})
        return {"products": products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/odoo/products")
def create_product(product: Product):
    try:
        product_data = {
            'name': product.name,
            'list_price': product.list_price
        }
        product_id = models.execute_kw(db, uid, password, 'product.product', 'create', [product_data])
        return {"message": "Product created", "product_id": product_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Root ---
@app.get("/")
def read_root():
    return {"message": "FastAPI is connected to Odoo!"}
