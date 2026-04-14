"""
Routes Analytics - tracking frontend + dashboard admin + profil personnel.
"""
from django.urls import path
from .views import (
    TrackEventView, TrackSearchView, RecordItemInteractionView,
    MyAnalyticsView, MySessionsView, MyEventsView, MyTasteProfileView,
    PlatformOverviewView, PlatformRealTimeView,
    UserListAnalyticsView, UserDetailAnalyticsView,
    UserSessionsAdminView, UserEventsAdminView,
    ItemInteractionHistoryView, GlobalItemInteractionsView,
    TopPagesView, FunnelAnalysisView,
    BehavioralAlertsView, ResolveAlertView,
    TopSearchesView, UserSegmentationView,
)

urlpatterns = [
    # Tracking frontend
    path("track/event/",       TrackEventView.as_view(),           name="analytics-track-event"),
    path("track/search/",      TrackSearchView.as_view(),          name="analytics-track-search"),
    path("track/interaction/", RecordItemInteractionView.as_view(), name="analytics-track-interaction"),

    # Profil personnel
    path("me/",          MyAnalyticsView.as_view(),  name="analytics-me"),
    path("me/sessions/", MySessionsView.as_view(),   name="analytics-my-sessions"),
    path("me/events/",   MyEventsView.as_view(),     name="analytics-my-events"),
    path("me/taste/",    MyTasteProfileView.as_view(), name="analytics-my-taste"),

    # Dashboard plateforme (admin)
    path("platform/overview/",          PlatformOverviewView.as_view(),      name="analytics-overview"),
    path("platform/realtime/",          PlatformRealTimeView.as_view(),      name="analytics-realtime"),
    path("platform/top-pages/",         TopPagesView.as_view(),              name="analytics-top-pages"),
    path("platform/funnel/",            FunnelAnalysisView.as_view(),        name="analytics-funnel"),
    path("platform/top-searches/",      TopSearchesView.as_view(),           name="analytics-searches"),
    path("platform/segmentation/",      UserSegmentationView.as_view(),      name="analytics-segmentation"),
    path("platform/item-interactions/", GlobalItemInteractionsView.as_view(), name="analytics-item-interactions"),

    # Utilisateurs (admin)
    path("users/",                          UserListAnalyticsView.as_view(),   name="analytics-users-list"),
    path("users/<uuid:user_id>/",           UserDetailAnalyticsView.as_view(), name="analytics-user-detail"),
    path("users/<uuid:user_id>/sessions/",  UserSessionsAdminView.as_view(),   name="analytics-user-sessions"),
    path("users/<uuid:user_id>/events/",    UserEventsAdminView.as_view(),     name="analytics-user-events"),
    path("users/<uuid:user_id>/interactions/", ItemInteractionHistoryView.as_view(), name="analytics-user-interactions"),

    # Alertes comportementales (admin)
    path("alerts/",                         BehavioralAlertsView.as_view(),  name="analytics-alerts"),
    path("alerts/<uuid:alert_id>/resolve/", ResolveAlertView.as_view(),      name="analytics-alert-resolve"),
]
