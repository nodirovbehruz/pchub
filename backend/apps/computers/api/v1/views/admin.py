from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.v1.permissions.admin import IsAdmin
from apps.computers.services.implementation.computer import ComputerService


@extend_schema(tags=["Admin - Computers"])
class ComputersStatusAPIView(APIView):
    """
    Admin-only endpoint: Get all computers with current status

    Returns list of all computers with:
    - Current online/offline status
    - Current user (if any)
    - Current game being played (if any)
    - Session duration
    - Last seen timestamp
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    service = ComputerService()

    def get(self, request):
        result = self.service.get_all_computers_status()
        return Response(result)
