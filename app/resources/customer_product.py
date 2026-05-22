# resources/customer_products.py
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.product import Product
from ..models.user import User
from ..extensions import db
from datetime import datetime
import json

def safe_str(v): return v if v is not None else ""
def safe_float(v): return v if v is not None else 0.0
def safe_int(v): return v if v is not None else 0

class CustomerGetProductsResource(Resource):
    @auth_required
    def get(self):
        """Get all available products for customers to purchase"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        search = request.args.get('search', '').strip()
        category = request.args.get('category', '').strip()
        status = request.args.get('status', 'active')
        min_price = request.args.get('min_price', 0, type=float)
        max_price = request.args.get('max_price', 100000, type=float)
        
        # Build query - only show active products with stock > 0
        query = Product.query.filter(
            Product.status == 'active',
            Product.stock_quantity > 0
        )
        
        # Apply filters
        if search:
            query = query.filter(
                db.or_(
                    Product.name.ilike(f'%{search}%'),
                    Product.description.ilike(f'%{search}%'),
                    Product.brand.ilike(f'%{search}%'),
                    Product.model.ilike(f'%{search}%')
                )
            )
        
        if category:
            query = query.filter(Product.category == category)
        
        if min_price > 0:
            query = query.filter(Product.price >= min_price)
        
        if max_price < 100000:
            query = query.filter(Product.price <= max_price)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        products = query.order_by(Product.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
        
        # Get merchant names for each product
        result = []
        for product in products:
            merchant = User.query.get(product.merchant_id)
            result.append({
                "id": product.id,
                "product_id": product.product_id,
                "name": product.name,
                "description": product.description,
                "category": product.category,
                "brand": product.brand,
                "model": product.model,
                "year": product.year,
                "price": safe_float(product.price),
                "stock_quantity": safe_int(product.stock_quantity),
                "main_image": product.main_image,
                "gallery_images": json.loads(product.gallery_images) if product.gallery_images else [],
                "merchant_id": product.merchant_id,
                "merchant_name": safe_str(merchant.business_name or merchant.full_name or merchant.phone),
                "status": product.status,
                "created_at": product.created_at.isoformat() if product.created_at else ""
            })
        
        return {
            "products": result,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }, 200


class CustomerGetProductDetailsResource(Resource):
    @auth_required
    def get(self, product_id):
        """Get single product details for customer"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        product = Product.query.get(product_id)
        
        if not product:
            return {"error": "Product not found"}, 404
        
        if product.status != 'active':
            return {"error": "Product is not available"}, 400
        
        merchant = User.query.get(product.merchant_id)
        
        return {
            "id": product.id,
            "product_id": product.product_id,
            "name": product.name,
            "description": product.description,
            "category": product.category,
            "brand": product.brand,
            "model": product.model,
            "year": product.year,
            "price": safe_float(product.price),
            "stock_quantity": safe_int(product.stock_quantity),
            "main_image": product.main_image,
            "gallery_images": json.loads(product.gallery_images) if product.gallery_images else [],
            "merchant_id": product.merchant_id,
            "merchant_name": safe_str(merchant.business_name or merchant.full_name or merchant.phone),
            "specifications": json.loads(product.specifications) if product.specifications else {},
            "created_at": product.created_at.isoformat() if product.created_at else ""
        }, 200


class CustomerGetProductCategoriesResource(Resource):
    @auth_required
    def get(self):
        """Get all product categories with counts"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        from sqlalchemy import func
        
        categories = db.session.query(
            Product.category,
            func.count(Product.id).label('count')
        ).filter(
            Product.status == 'active',
            Product.stock_quantity > 0
        ).group_by(Product.category).all()
        
        return {
            "categories": [{
                "name": c[0] if c[0] else "Uncategorized",
                "count": c[1]
            } for c in categories if c[0]]
        }, 200