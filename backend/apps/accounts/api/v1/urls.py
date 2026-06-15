from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.api.v1.views.account import (
    LoginView,
    LogoutAPIView,
    UserProfileView,
    UserRegistrationView,
    UsersListView,
    EmployeeListAPIView,
    EmployeeManageAPIView,
    UserSearchAPIView,
    ClientCreateAPIView,
)

app_name = "accounts"

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="user-registration"),
    path("login/", LoginView.as_view(), name="user-login"),
    path("logout/", LogoutAPIView.as_view(), name="user-logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("profile/", UserProfileView.as_view(), name="user-profile"),
    path("users/", UsersListView.as_view(), name="users-list"),
    path("employees/", EmployeeListAPIView.as_view(), name="employee-list"),
    path("employees/<str:pk>/", EmployeeManageAPIView.as_view(), name="employee-manage"),
    path("users/search/", UserSearchAPIView.as_view(), name="user-search"),
    path("clients/", ClientCreateAPIView.as_view(), name="client-create"),
]
