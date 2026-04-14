from django.urls import path
from .views import HomepageFeedView

urlpatterns = [
    path("homepage/", HomepageFeedView.as_view(), name="homepage-feed"),
]
