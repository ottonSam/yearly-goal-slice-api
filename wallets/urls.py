from rest_framework.routers import DefaultRouter

from .views import ExpenseCategoryViewSet, WalletViewSet


router = DefaultRouter()
router.register('wallets/categories', ExpenseCategoryViewSet, basename='wallet-expense-category')
router.register('wallets', WalletViewSet, basename='wallet')

urlpatterns = router.urls
