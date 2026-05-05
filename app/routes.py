from flask_restful import Api

from .resources.admin import (
    PendingUsersResource,
    ApproveUserResource,
    RejectUserResource,
    GetCustomersResource,
    CustomerResource,
    GetMerchantsResource,
    MerchantResource,
    VerifyMerchantResource,
    MerchantStatsResource,
    BulkUpdateCustomersResource,
    SearchCustomersResource,
    CustomerStatsResource,
    ExportCustomersResource
)
from .resources.auth import RegisterResource, LoginResource
from .resources.protected import ProtectedResource
from .resources.admin_stats import AdminStatsResource

def register_routes(app):
    api = Api(app)

    # ============================================
    # AUTHENTICATION ROUTES
    # ============================================
    api.add_resource(RegisterResource, "/register")
    api.add_resource(LoginResource, "/login")

    # ============================================
    # ADMIN - USER MANAGEMENT ROUTES
    # ============================================
    # User approval/rejection
    api.add_resource(PendingUsersResource, "/admin/pending-users")
    api.add_resource(ApproveUserResource, "/admin/approve/<int:user_id>")
    api.add_resource(RejectUserResource, "/admin/reject/<int:user_id>")
    
    # Admin statistics
    api.add_resource(AdminStatsResource, "/admin/stats")

    # ============================================
    # ADMIN - CUSTOMER ROUTES
    # ============================================
    # Get all customers
    api.add_resource(GetCustomersResource, "/admin/customers")
    
    # Single customer operations (Get, Update, Delete)
    api.add_resource(CustomerResource, "/admin/customers/<int:customer_id>")
    
    # Customer bulk operations
    api.add_resource(BulkUpdateCustomersResource, "/admin/customers/bulk-update")
    
    # Customer search and filters
    api.add_resource(SearchCustomersResource, "/admin/customers/search")
    
    # Customer statistics
    api.add_resource(CustomerStatsResource, "/admin/customers/stats")
    
    # Customer export
    api.add_resource(ExportCustomersResource, "/admin/customers/export")

    # ============================================
    # ADMIN - MERCHANT ROUTES
    # ============================================
    # Get all merchants
    api.add_resource(GetMerchantsResource, "/admin/merchants")
    
    # Single merchant operations (Get, Update, Delete)
    api.add_resource(MerchantResource, "/admin/merchants/<int:merchant_id>")
    
    # Merchant verification
    api.add_resource(VerifyMerchantResource, "/admin/merchants/verify/<int:merchant_id>")
    
    # Merchant statistics
    api.add_resource(MerchantStatsResource, "/admin/merchants/stats")

    # ============================================
    # PROTECTED ROUTES (requires authentication)
    # ============================================
    api.add_resource(ProtectedResource, "/protected")