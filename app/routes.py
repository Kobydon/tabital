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
    ExportCustomersResource,
    MerchantKYCResource,
    MerchantCommissionResource,
    MerchantSettlementResource,
    GetCurrentUserResource
)
from .resources.transaction import (
    GetTransactionsResource,
    CreateTransactionResource,
    UpdateTransactionStatusResource,
    GetTransactionStatsResource,
    DeleteTransactionResource
)
from .resources.document import (
    GetMerchantDocumentsResource,
    UploadDocumentResource,
    VerifyDocumentResource,
    DeleteDocumentResource
)

from .resources.instalment import (
    GetMerchantInstalmentsResource,
    CreateInstalmentPlanResource,
    UpdateInstalmentPlanResource,
    DeleteInstalmentPlanResource,
    GetInstalmentPlanDetailsResource,
    RecordInstalmentPaymentResource
)

from .resources.auth import RegisterResource, LoginResource
from .resources.protected import ProtectedResource
from .resources.admin_stats import AdminStatsResource

from .resources.transaction import (
    MerchantGetTransactionsResource,
    MerchantGetTransactionStatsResource,
    MerchantUpdateTransactionStatusResource,
    MerchantUpdateTransactionResource,
    MerchantRefundTransactionResource,
    MerchantExportTransactionsResource
)

from .resources.merchant_customers import (
    MerchantGetCustomersResource,
    MerchantGetCustomerDetailsResource,
    MerchantUpdateCustomerResource,
    MerchantGetCustomerStatsResource,
    MerchantExportCustomersResource
)

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
    api.add_resource(PendingUsersResource, "/admin/pending-users")
    api.add_resource(ApproveUserResource, "/admin/approve/<int:user_id>")
    api.add_resource(RejectUserResource, "/admin/reject/<int:user_id>")
    api.add_resource(AdminStatsResource, "/admin/stats")

    # ============================================
    # ADMIN - CUSTOMER ROUTES
    # ============================================
    api.add_resource(GetCustomersResource, "/admin/customers")
    api.add_resource(CustomerResource, "/admin/customers/<int:customer_id>")
    api.add_resource(BulkUpdateCustomersResource, "/admin/customers/bulk-update")
    api.add_resource(SearchCustomersResource, "/admin/customers/search")
    api.add_resource(CustomerStatsResource, "/admin/customers/stats")
    api.add_resource(ExportCustomersResource, "/admin/customers/export")

    # ============================================
    # ADMIN - MERCHANT ROUTES
    # ============================================
    api.add_resource(GetMerchantsResource, "/admin/merchants")
    api.add_resource(MerchantResource, "/admin/merchants/<int:merchant_id>")
    api.add_resource(VerifyMerchantResource, "/admin/merchants/verify/<int:merchant_id>")
    api.add_resource(MerchantStatsResource, "/admin/merchants/stats")
    
    # Merchant specialized endpoints
    api.add_resource(MerchantKYCResource, "/admin/merchants/<int:merchant_id>/kyc")
    api.add_resource(MerchantCommissionResource, "/admin/merchants/<int:merchant_id>/commission")
    api.add_resource(MerchantSettlementResource, "/admin/merchants/<int:merchant_id>/settlement")

    # ============================================
    # ADMIN - DOCUMENT ROUTES
    # ============================================
    api.add_resource(GetMerchantDocumentsResource, "/admin/merchants/<int:merchant_id>/documents")
    api.add_resource(UploadDocumentResource, "/admin/merchants/<int:merchant_id>/documents/upload")
    api.add_resource(VerifyDocumentResource, "/admin/documents/<int:document_id>/verify")
    api.add_resource(DeleteDocumentResource, "/admin/documents/<int:document_id>")

    # ============================================
    # TRANSACTION ROUTES
    # ============================================
    api.add_resource(GetTransactionsResource, "/transactions")
    api.add_resource(CreateTransactionResource, "/transactions/create")
    api.add_resource(UpdateTransactionStatusResource, "/transactions/<int:transaction_id>/status")
    api.add_resource(GetTransactionStatsResource, "/transactions/stats")
    api.add_resource(DeleteTransactionResource, "/transactions/<int:transaction_id>")


    #===========================================
    # CURRENT USER ROUTE
    #===========================================
    api.add_resource(GetCurrentUserResource, "/admin/get_current_user")
    # ============================================
    # PROTECTED ROUTES
    # ============================================

    # Add to imports

# Add to register_routes function:

    # ============================================
    # INSTALMENT PLAN ROUTES
    # ============================================
    api.add_resource(GetMerchantInstalmentsResource, "/merchant/instalments")
    api.add_resource(CreateInstalmentPlanResource, "/merchant/instalments/create")
    api.add_resource(UpdateInstalmentPlanResource, "/merchant/instalments/<int:plan_id>")
    api.add_resource(DeleteInstalmentPlanResource, "/merchant/instalments/<int:plan_id>")
    api.add_resource(GetInstalmentPlanDetailsResource, "/merchant/instalments/<int:plan_id>/details")
    api.add_resource(RecordInstalmentPaymentResource, "/merchant/instalments/<int:plan_id>/pay")

    api.add_resource(ProtectedResource, "/protected")

    # Add to imports

# Add to register_routes function:

    # ============================================
    # MERCHANT TRANSACTION ROUTES
    # ============================================
    api.add_resource(MerchantGetTransactionsResource, "/merchant/transactions")
    api.add_resource(MerchantGetTransactionStatsResource, "/merchant/transactions/stats")
    api.add_resource(MerchantUpdateTransactionStatusResource, "/merchant/transactions/<int:transaction_id>/status")
    api.add_resource(MerchantUpdateTransactionResource, "/merchant/transactions/<int:transaction_id>")
    api.add_resource(MerchantRefundTransactionResource, "/merchant/transactions/<int:transaction_id>/refund")
    api.add_resource(MerchantExportTransactionsResource, "/merchant/transactions/export")

    # Add to imports


# Add to register_routes function:

    # ============================================
    # MERCHANT CUSTOMER ROUTES
    # ============================================
    api.add_resource(MerchantGetCustomersResource, "/merchant/customers")
    api.add_resource(MerchantGetCustomerDetailsResource, "/merchant/customers/<int:customer_id>")
    api.add_resource(MerchantUpdateCustomerResource, "/merchant/customers/<int:customer_id>")
    api.add_resource(MerchantGetCustomerStatsResource, "/merchant/customers/stats")
    api.add_resource(MerchantExportCustomersResource, "/merchant/customers/export")