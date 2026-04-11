from django.urls import path
from .views import (
    OrderCreateView, OrderListView, OrderDetailView,
    OrderStatusView, OrderCancelView, OrderReviewView,
)

urlpatterns = [
    path("", OrderCreateView.as_view(), name="order-create"),
    path("list/", OrderListView.as_view(), name="order-list"),
    path("<uuid:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("<uuid:pk>/status/", OrderStatusView.as_view(), name="order-status"),
    path("<uuid:pk>/cancel/",   OrderCancelView.as_view(), name="order-cancel"),
    path("<uuid:pk>/review/", OrderReviewView.as_view(), name="order-review"),
]
