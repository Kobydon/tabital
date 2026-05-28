# app/routes.py
from flask_restful import Api

# Admin Resources
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
    GetCurrentUserResource,
     AdminApproveOrderResource,
)

# Transaction Resources
from .resources.transaction import (
    GetTransactionsResource,
    CreateTransactionResource,
    MerchantPayoutStatsResource,
    MerchantRecentPayoutsResource,
    UpdateTransactionStatusResource,
    GetTransactionStatsResource,
    DeleteTransactionResource,
    MerchantGetTransactionsResource,
    MerchantGetTransactionStatsResource,
    MerchantUpdateTransactionStatusResource,
    MerchantUpdateTransactionResource,
    MerchantRefundTransactionResource,
    MerchantExportTransactionsResource
)

# Document Resources
from .resources.document import (
    GetMerchantDocumentsResource,
    UploadDocumentResource,
    VerifyDocumentResource,
    DeleteDocumentResource
)


from .services.auth_service import (

    ForgotPasswordResource,
    VerifyResetOTPResource,
    ResetPasswordResource
)


# Auth Resources
from .resources.auth import CheckUserExistsResource, RegisterResource, LoginResource

# Protected Resources
from .resources.protected import ProtectedResource

# Admin Stats Resources
from .resources.admin_stats import AdminStatsResource

# Merchant Dashboard Resources
from .resources.merchant_dashboard import (
    MerchantDashboardStatsResource,
    MerchantSalesChartResource,
    MerchantRecentTransactionsResource,
    MerchantInstalmentsOverviewResource,
    MerchantSettlementInfoResource,
    MerchantAccountStatusResource,
    MerchantQuickActionsResource
)

# Merchant Customers Resources
from .resources.merchant_customers import (
    MerchantGetCustomersResource,
    MerchantGetCustomerDetailsResource,
    MerchantUpdateCustomerResource,
    MerchantGetCustomerStatsResource,
    MerchantExportCustomersResource
)

# Merchant Settlements Resources
from .resources.merchant_settlements import (
    MerchantGetSettlementsResource,
    MerchantGetSettlementSummaryResource,
    MerchantRequestPayoutResource,
    MerchantUpdateSettlementSettingsResource,
    MerchantGetSettlementDetailsResource
)

# Merchant Disputes Resources
from .resources.merchant_disputes import (
    MerchantGetDisputesResource,
    MerchantGetDisputeStatsResource,
    MerchantGetDisputeDetailsResource,
    MerchantUpdateDisputeResource,
    MerchantAcceptDisputeResource,
    MerchantRejectDisputeResource,
    MerchantEscalateDisputeResource
)

# Merchant Reports Resources
from .resources.merchant_reports import (
    MerchantSalesReportResource,
    MerchantTransactionReportResource,
    MerchantCustomerReportResource,
    MerchantFinancialReportResource,
    MerchantInstalmentReportResource,
    MerchantExportReportResource
)

# Merchant Settings Resources
from .resources.merchant_settings import (
    MerchantGetProfileResource,
    MerchantUpdateProfileResource,
    MerchantUpdatePasswordResource,
    MerchantUpdatePaymentSettingsResource,
    MerchantGetNotificationSettingsResource,
    MerchantUpdateNotificationSettingsResource,
    MerchantGetPreferencesResource,
    MerchantUpdatePreferencesResource,
    MerchantUpdateKYCResource,
    MerchantUploadDocumentResource,
    MerchantGetActivityLogResource
)

# Customer Resources
from .resources.customer_dashboard import (
    CustomerDashboardStatsResource,
    CustomerPaymentOverviewResource,
    CustomerUpcomingPaymentsResource,
    CustomerRecentTransactionsResource,
    CustomerInstalmentsResource,
    CustomerPlanDetailsResource,
    CustomerMakePaymentResource
)

from .resources.customer_profile import (
    CustomerGetProfileResource,
    CustomerUpdateProfileResource,
    CustomerUpdatePasswordResource,
    CustomerGetKYCStatusResource,
    CustomerUploadKYCResource,
    CustomerGetActivityLogResource
)

from .resources.customer_notifications import (
    CustomerGetNotificationsResource,
    CustomerMarkNotificationReadResource,
    CustomerMarkAllNotificationsReadResource,
    CustomerGetNotificationSettingsResource,
    CustomerUpdateNotificationSettingsResource,
    CustomerUnreadNotificationCountResource
)

# routes.py - Add these imports

from .resources.customer_payments import (
    CustomerGetPaymentsResource,
    CustomerGetPaymentStatsResource,
    CustomerDownloadReceiptResource,
    CustomerPaidPaymentsResource,
    CustomerPaymentReminderResource,
    CustomerMakePaymentResource
)

from .resources.customer_transactions import (
    CustomerGetTransactionsResource,
    CustomerGetTransactionDetailsResource,
    CustomerGetTransactionStatsResource,
    CustomerExportTransactionsResource
)

from .resources.customer_support import (
    CustomerCreateTicketResource,
    CustomerGetTicketsResource,
    CustomerGetTicketDetailsResource,
    CustomerAddTicketMessageResource,
    CustomerCloseTicketResource
)

# System Settings Resources
from .resources.system_settings import (
    SystemSettingsResource,
    InstallmentCalculatorResource,
    LateFeeCalculatorResource
)

from .resources.system_settings import (
    SystemSettingsResource,
    InstallmentOptionsResource,  # Add this
    InstallmentCalculatorResource,
    LateFeeCalculatorResource
)

from .resources.product import (
    MerchantProductsResource,
    MerchantProductDetailResource
)

from .resources.admin_orders import (
    AdminGetOrdersResource,
   
    AdminRejectOrderResource
)
from .resources.merchant_orders import (
    MerchantGetOrdersResource,
    MerchantUpdateDeliveryStatusResource
)
from .resources.customer_purchase import (
    CustomerPurchaseResource,
    CustomerGetOrdersResource
)
# routes.py - Add these imports
from .resources.customer_product import (
    CustomerGetProductsResource,
    CustomerGetProductDetailsResource,
    CustomerGetProductCategoriesResource
)
from .resources.customer_payments import (
    CustomerGetPaymentsResource,
    CustomerGetPaymentStatsResource,
    CustomerDownloadReceiptResource
)
# Add to routes.py

# routes.py - Add these imports

from .resources.customer_document import (
    CustomerGetDocumentsResource,
    CustomerUploadDocumentsResource,
    CustomerGetKYCStatusResource,
    AdminVerifyDocumentResource,
    AdminGetPendingKYCResource
)

# routes.py - Add these imports and routes

from .resources.merchant_document import (
    MerchantGetDocumentsResource,
    MerchantUploadDocumentsResource,
    MerchantGetKYCStatusResource,
    MerchantGetBankDetailsResource,
    MerchantUpdateBankDetailsResource,
    AdminGetPendingMerchantKYCResource,
    AdminVerifyMerchantDocumentResource,
    AdminVerifyMerchantCompleteResource
)

from .resources.notification import (
    GetNotificationsResource,
    MarkNotificationReadResource,
    MarkAllNotificationsReadResource,
    DeleteNotificationResource,
    ClearAllNotificationsResource,
    GetUnreadCountResource
)

# routes.py - Add these imports

from .resources.merchant_notifications import (
    MerchantGetNotificationsResource,
    MerchantMarkNotificationReadResource,
    MerchantMarkAllNotificationsReadResource,
    MerchantGetNotificationSettingsResource,
    MerchantUpdateNotificationSettingsResource,
    MerchantUnreadNotificationCountResource,
    MerchantDeleteNotificationResource,
    MerchantClearAllNotificationsResource
)
from .resources.admin_kyc import (
    AdminGetPendingKYCResource,
    AdminGetVerifiedKYCResource,
    AdminGetRejectedKYCResource,
    AdminGetMerchantKYCResource,
    AdminApproveKYCResource,
    AdminRejectKYCResource,
    AdminApproveDocumentResource,
    AdminRejectDocumentResource
)

# In routes.py
from .resources.customer_document import CustomerUploadOptionalDocumentResource

# In register_routes function, add:

# ============================================
# MERCHANT NOTIFICATION ROUTES
# ============================================


# In register_routes function, add:

# ============================================
# MERCHANT DOCUMENT ROUTES
# ============================================

# Add to register_routes function:

# ============================================
# CUSTOMER DOCUMENT ROUTES
# ============================================

# Add to register_routes function:

# Add to register_routes function:
# ============================================
# CUSTOMER PRODUCT ROUTES
# ============================================


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
    # ADMIN - SYSTEM SETTINGS ROUTES
    # ============================================
    api.add_resource(SystemSettingsResource, "/admin/settings/charges")
    api.add_resource(InstallmentCalculatorResource, "/installment/calculate")
    api.add_resource(LateFeeCalculatorResource, "/installment/late-fee")

    # ============================================
    # TRANSACTION ROUTES
    # ============================================
    api.add_resource(GetTransactionsResource, "/transactions")
    api.add_resource(CreateTransactionResource, "/transactions/create")
    api.add_resource(UpdateTransactionStatusResource, "/transactions/<int:transaction_id>/status")
    api.add_resource(GetTransactionStatsResource, "/transactions/stats")
    api.add_resource(DeleteTransactionResource, "/transactions/<int:transaction_id>")

    # ============================================
    # CURRENT USER ROUTE
    # ============================================
    api.add_resource(GetCurrentUserResource, "/admin/get_current_user")

    # ============================================
    # MERCHANT DASHBOARD ROUTES
    # ============================================
    api.add_resource(MerchantDashboardStatsResource, "/merchant/dashboard/stats")
    api.add_resource(MerchantSalesChartResource, "/merchant/dashboard/sales-chart")
    api.add_resource(MerchantRecentTransactionsResource, "/merchant/transactions/recent")
    api.add_resource(MerchantInstalmentsOverviewResource, "/merchant/instalments/overview")
    api.add_resource(MerchantSettlementInfoResource, "/merchant/settlements/info")
    api.add_resource(MerchantAccountStatusResource, "/merchant/account/status")
    api.add_resource(MerchantQuickActionsResource, "/merchant/quick-actions")

    # ============================================
    # MERCHANT TRANSACTION ROUTES
    # ============================================
    api.add_resource(MerchantGetTransactionsResource, "/merchant/transactions")
    api.add_resource(MerchantGetTransactionStatsResource, "/merchant/transactions/stats")
    api.add_resource(MerchantUpdateTransactionStatusResource, "/merchant/transactions/<int:transaction_id>/status")
    api.add_resource(MerchantUpdateTransactionResource, "/merchant/transactions/<int:transaction_id>")
    api.add_resource(MerchantRefundTransactionResource, "/merchant/transactions/<int:transaction_id>/refund")
    api.add_resource(MerchantExportTransactionsResource, "/merchant/transactions/export")

    # ============================================
    # MERCHANT CUSTOMER ROUTES
    # ============================================
    api.add_resource(MerchantGetCustomersResource, "/merchant/customers")
    api.add_resource(MerchantGetCustomerDetailsResource, "/merchant/customers/<int:customer_id>")
    api.add_resource(MerchantUpdateCustomerResource, "/merchant/customers/<int:customer_id>")
    api.add_resource(MerchantGetCustomerStatsResource, "/merchant/customers/stats")
    api.add_resource(MerchantExportCustomersResource, "/merchant/customers/export")

    # ============================================
    # MERCHANT SETTLEMENT ROUTES
    # ============================================
    api.add_resource(MerchantGetSettlementsResource, "/merchant/settlements")
    api.add_resource(MerchantGetSettlementSummaryResource, "/merchant/settlements/summary")
    api.add_resource(MerchantRequestPayoutResource, "/merchant/settlements/request-payout")
    api.add_resource(MerchantUpdateSettlementSettingsResource, "/merchant/settlements/settings")
    api.add_resource(MerchantGetSettlementDetailsResource, "/merchant/settlements/<string:settlement_id>")

    # ============================================
    # MERCHANT DISPUTE ROUTES
    # ============================================
    api.add_resource(MerchantGetDisputesResource, "/merchant/disputes")
    api.add_resource(MerchantGetDisputeStatsResource, "/merchant/disputes/stats")
    api.add_resource(MerchantGetDisputeDetailsResource, "/merchant/disputes/<int:dispute_id>")
    api.add_resource(MerchantUpdateDisputeResource, "/merchant/disputes/<int:dispute_id>")
    api.add_resource(MerchantAcceptDisputeResource, "/merchant/disputes/<int:dispute_id>/accept")
    api.add_resource(MerchantRejectDisputeResource, "/merchant/disputes/<int:dispute_id>/reject")
    api.add_resource(MerchantEscalateDisputeResource, "/merchant/disputes/<int:dispute_id>/escalate")

    # ============================================
    # MERCHANT REPORT ROUTES
    # ============================================
    api.add_resource(MerchantSalesReportResource, "/merchant/reports/sales")
    api.add_resource(MerchantTransactionReportResource, "/merchant/reports/transactions")
    api.add_resource(MerchantCustomerReportResource, "/merchant/reports/customers")
    api.add_resource(MerchantFinancialReportResource, "/merchant/reports/financial")
    api.add_resource(MerchantInstalmentReportResource, "/merchant/reports/instalments")
    api.add_resource(MerchantExportReportResource, "/merchant/reports/export")

    # ============================================
    # MERCHANT SETTINGS ROUTES
    # ============================================
    api.add_resource(MerchantGetProfileResource, "/merchant/settings/profile")
    api.add_resource(MerchantUpdateProfileResource, "/merchant/settings/profile")
    api.add_resource(MerchantUpdatePasswordResource, "/merchant/settings/password")
    api.add_resource(MerchantUpdatePaymentSettingsResource, "/merchant/settings/payment")
    api.add_resource(MerchantGetNotificationSettingsResource, "/merchant/settings/notifications")
    api.add_resource(MerchantUpdateNotificationSettingsResource, "/merchant/settings/notifications")
    api.add_resource(MerchantGetPreferencesResource, "/merchant/settings/preferences")
    api.add_resource(MerchantUpdatePreferencesResource, "/merchant/settings/preferences")
    api.add_resource(MerchantUpdateKYCResource, "/merchant/settings/kyc")
    api.add_resource(MerchantUploadDocumentResource, "/merchant/settings/upload-document")
    api.add_resource(MerchantGetActivityLogResource, "/merchant/settings/activity-log")

    # ============================================
    # CUSTOMER DASHBOARD ROUTES
    # ============================================
    api.add_resource(CustomerDashboardStatsResource, "/customer/dashboard/stats")
    api.add_resource(CustomerPaymentOverviewResource, "/customer/payment-overview")
    api.add_resource(CustomerUpcomingPaymentsResource, "/customer/upcoming-payments")
    api.add_resource(CustomerRecentTransactionsResource, "/customer/recent-transactions")
    api.add_resource(CustomerInstalmentsResource, "/customer/instalments")
    api.add_resource(CustomerPlanDetailsResource, "/customer/instalments/<int:plan_id>")
    api.add_resource(CustomerMakePaymentResource, "/customer/payments/make")

    # ============================================
    # CUSTOMER PROFILE ROUTES
    # ============================================
    api.add_resource(CustomerGetProfileResource, "/customer/profile")
    api.add_resource(CustomerUpdateProfileResource, "/customer/profile")
    api.add_resource(CustomerUpdatePasswordResource, "/customer/password")
    api.add_resource(CustomerGetKYCStatusResource, "/customer/kyc/status")
    api.add_resource(CustomerUploadKYCResource, "/customer/kyc/upload")
    api.add_resource(CustomerGetActivityLogResource, "/customer/settings/activity-log")

    # ============================================
    # CUSTOMER NOTIFICATION ROUTES
    # ============================================
    api.add_resource(CustomerGetNotificationsResource, "/customer/notifications")
    api.add_resource(CustomerMarkNotificationReadResource, "/customer/notifications/<string:notification_id>/read")
    api.add_resource(CustomerMarkAllNotificationsReadResource, "/customer/notifications/mark-all-read")
    api.add_resource(CustomerGetNotificationSettingsResource, "/customer/notifications/settings")
    api.add_resource(CustomerUpdateNotificationSettingsResource, "/customer/notifications/settings")
    api.add_resource(CustomerUnreadNotificationCountResource, "/customer/notifications/unread-count")

    # ============================================
    # CUSTOMER PAYMENT ROUTES
    # ============================================
    api.add_resource(CustomerPaymentReminderResource, "/customer/payments/reminder")

    # ============================================
    # CUSTOMER TRANSACTION ROUTES
    # ============================================
    api.add_resource(CustomerGetTransactionsResource, "/customer/transactions")
    api.add_resource(CustomerGetTransactionDetailsResource, "/customer/transactions/<int:transaction_id>")
    api.add_resource(CustomerGetTransactionStatsResource, "/customer/transactions/stats")
    api.add_resource(CustomerExportTransactionsResource, "/customer/transactions/export")

    # ============================================
    # CUSTOMER SUPPORT ROUTES
    # ============================================
    api.add_resource(CustomerCreateTicketResource, "/customer/support/ticket")
    api.add_resource(CustomerGetTicketsResource, "/customer/support/tickets")
    api.add_resource(CustomerGetTicketDetailsResource, "/customer/support/tickets/<int:ticket_id>")
    api.add_resource(CustomerAddTicketMessageResource, "/customer/support/tickets/<int:ticket_id>/reply")
    api.add_resource(CustomerCloseTicketResource, "/customer/support/tickets/<int:ticket_id>/close")

    # ============================================
    # PROTECTED ROUTES
    # ============================================

    # Add to imports in routes.py

# Add to register_routes function:
    # api.add_resource(SystemSettingsResource, "/admin/settings/charges")
    api.add_resource(InstallmentOptionsResource, "/admin/settings/installments")  # Add this
    # api.add_resource(InstallmentCalculatorResource, "/installment/calculate")
    # api.add_resource(LateFeeCalculatorResource, "/installment/late-fee")

    # resources/__init__.py - Add product routes



# Add to register_routes function:
    api.add_resource(MerchantProductsResource, "/merchant/products")
    api.add_resource(MerchantProductDetailResource, "/merchant/products/<int:product_id>")
    api.add_resource(ProtectedResource, "/protected")
        
    api.add_resource(CustomerUploadOptionalDocumentResource, "/customer/documents/upload-optional")
    # Add to routes.py imports


# Add to register_routes function:
# ============================================
# ADMIN ORDER ROUTES
# ============================================
    api.add_resource(AdminGetOrdersResource, "/admin/orders")
    api.add_resource(AdminApproveOrderResource, "/admin/orders/<int:order_id>/approve")
    api.add_resource(AdminRejectOrderResource, "/admin/orders/<int:order_id>/reject")

    # ============================================
    # MERCHANT ORDER ROUTES
    # ============================================
    api.add_resource(MerchantGetOrdersResource, "/merchant/orders")
    api.add_resource(MerchantUpdateDeliveryStatusResource, "/merchant/orders/<int:order_id>/delivery")

    # ============================================
    # CUSTOMER PURCHASE ROUTES
    # ============================================
    api.add_resource(CustomerPurchaseResource, "/customer/purchase")
    api.add_resource(CustomerGetOrdersResource, "/customer/orders")




    api.add_resource(CustomerGetProductsResource, "/customer/products")
    api.add_resource(CustomerGetProductDetailsResource, "/customer/products/<int:product_id>")
    api.add_resource(CustomerGetProductCategoriesResource, "/customer/products/categories")


    # Add to routes.py imports


# Add to register_routes function:
# ============================================
# CUSTOMER PAYMENTS ROUTES
# ============================================
    api.add_resource(CustomerGetPaymentsResource, "/customer/payments")
    api.add_resource(CustomerGetPaymentStatsResource, "/customer/payments/stats")
    api.add_resource(CustomerDownloadReceiptResource, "/customer/payments/<int:payment_id>/receipt")
    # api.add_resource(CustomerInstalmentsResource, "/customer/instalments")
    # In register_routes function, add:

# ============================================
# CUSTOMER PAYMENT ROUTES
# ============================================
    api.add_resource(CustomerPaidPaymentsResource, "/customer/paid-payments")

    api.add_resource(CustomerGetDocumentsResource, "/customer/documents")
    api.add_resource(CustomerUploadDocumentsResource, "/customer/documents/upload")
    # api.add_resource(CustomerGetKYCStatusResource, "/customer/kyc/status")

# ============================================
# ADMIN DOCUMENT VERIFICATION ROUTES
# ============================================
    api.add_resource(AdminGetPendingKYCResource, "/admin/kyc/pending")
    api.add_resource(AdminVerifyDocumentResource, "/admin/documents/<int:document_id>/verify")
    api.add_resource(MerchantGetDocumentsResource, "/merchant/documents")
    api.add_resource(MerchantUploadDocumentsResource, "/merchant/documents/upload")
    api.add_resource(MerchantGetKYCStatusResource, "/merchant/kyc/status")
    api.add_resource(MerchantGetBankDetailsResource, "/merchant/bank-details")
    api.add_resource(MerchantUpdateBankDetailsResource, "/merchant/bank-details")

    # ============================================
    # ADMIN MERCHANT VERIFICATION ROUTES
    # ============================================
    api.add_resource(AdminGetPendingMerchantKYCResource, "/admin/merchant/kyc/pending")
    api.add_resource(AdminVerifyMerchantDocumentResource, "/admin/merchant/documents/<int:document_id>/verify")
    api.add_resource(AdminVerifyMerchantCompleteResource, "/admin/merchant/<int:merchant_id>/verify")
    # routes.py - Add notification routes


# In register_routes function, add:

# ============================================
# NOTIFICATION ROUTES
# ============================================
    api.add_resource(GetNotificationsResource, "/notifications")
    api.add_resource(MarkNotificationReadResource, "/notifications/<int:notification_id>/read")
    api.add_resource(MarkAllNotificationsReadResource, "/notifications/mark-all-read")
    api.add_resource(DeleteNotificationResource, "/notifications/<int:notification_id>")
    api.add_resource(ClearAllNotificationsResource, "/notifications/clear-all")
    api.add_resource(GetUnreadCountResource, "/notifications/unread-count")


    # api.add_resource(MerchantGetNotificationsResource, "/merchant/notifications")
    api.add_resource(MerchantMarkNotificationReadResource, "/merchant/notifications/<string:notification_id>/read")
    api.add_resource(MerchantMarkAllNotificationsReadResource, "/merchant/notifications/mark-all-read")
    # api.add_resource(MerchantGetNotificationSettingsResource, "/merchant/notifications/settings")
    # api.add_resource(MerchantUpdateNotificationSettingsResource, "/merchant/notifications/settings")
    api.add_resource(MerchantUnreadNotificationCountResource, "/merchant/notifications/unread-count")
    api.add_resource(MerchantDeleteNotificationResource, "/merchant/notifications/<string:notification_id>")
    api.add_resource(MerchantClearAllNotificationsResource, "/merchant/notifications/clear-all")
    # Add to your API routes
    api.add_resource(MerchantPayoutStatsResource, '/merchant/payouts/stats')
    api.add_resource(MerchantRecentPayoutsResource, '/merchant/payouts/recent')
    # routes.py - Add these imports


    api.add_resource(ForgotPasswordResource, "/forgot-password")
    # routes.py - Change the route path
    api.add_resource(VerifyResetOTPResource, "/api/verify-otp")
    api.add_resource(ResetPasswordResource, "/reset-password")
    # In your main app file or routes file
    api.add_resource(CheckUserExistsResource, '/api/check-user-exists')
    # Add these to your route registration


# KYC/KYB Admin Routes
    api.add_resource(AdminGetPendingKYCResource, '/admin/kyc/pending')
    api.add_resource(AdminGetVerifiedKYCResource, '/admin/kyc/verified')
    api.add_resource(AdminGetRejectedKYCResource, '/admin/kyc/rejected')
    api.add_resource(AdminGetMerchantKYCResource, '/admin/kyc/merchant/<int:merchant_id>')
    api.add_resource(AdminApproveKYCResource, '/admin/kyc/approve/<int:merchant_id>')
    api.add_resource(AdminRejectKYCResource, '/admin/kyc/reject/<int:merchant_id>')
    api.add_resource(AdminApproveDocumentResource, '/admin/kyc/document/approve/<int:document_id>')
    api.add_resource(AdminRejectDocumentResource, '/admin/kyc/document/reject/<int:document_id>')
    
    # ... rest of your routes

