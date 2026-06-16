from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.accounts.api.v1.serializers.account import (
    UserListSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)
from apps.accounts.repositories.implementation.account import AccountRepository
from apps.accounts.services.implementation.auth import AuthService, SessionAlreadyActiveError
from apps.accounts.services.implementation.user import UserCreateService


@extend_schema(tags=["Account"])
class UserRegistrationView(generics.CreateAPIView):
    """User registration with email and password"""

    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    service = UserCreateService(repository=AccountRepository())

    def perform_create(self, serializer):
        data = serializer.validated_data.copy()
        self.service.execute(data)


@extend_schema(tags=["Account"])
class LoginView(generics.CreateAPIView):
    """User login with username and password"""

    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = "login"  # ScopedRateThrottle: 10/min/IP — anti brute-force
    service = AuthService(account_repository=AccountRepository())

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = self.service.login_user(
                username=serializer.validated_data["username"],
                password=serializer.validated_data["password"],
                hardware_id=serializer.validated_data.get("hardware_id"),
            )
        except SessionAlreadyActiveError:
            return Response(
                {
                    "error": "session_already_active",
                    "detail": "Этот аккаунт уже активен на другом компьютере. Сначала выйдите из системы на том устройстве."
                },
                status=status.HTTP_423_LOCKED,
            )

        # Audit log — only for staff logins (skip regular clients to avoid noise)
        try:
            user = result.get("user")
            if user and getattr(user, "user_type", "") in ("owner", "manager", "operator", "admin"):
                from apps.billing.models import OperationLog, LogAction
                club_id = getattr(request, "current_club_id", None)
                OperationLog.objects.create(
                    club_id=club_id, subject=user,
                    object_type="Auth", object_id=str(user.pk),
                    object_repr=f"Вход: {user.username}",
                    action=LogAction.AUTH_LOGIN,
                    payload={"username": user.username},
                )
        except Exception:
            pass

        return Response(
            {
                "refresh": result["refresh"],
                "access": result["access"],
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Account"])
class UserProfileView(generics.RetrieveAPIView):
    """User profile view"""

    queryset = AccountRepository().none()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(tags=["Account"])
class UsersListView(generics.ListAPIView):
    """Users list view"""

    queryset = AccountRepository().get_users()
    serializer_class = UserListSerializer
    permission_classes = [permissions.IsAuthenticated]


@extend_schema(tags=["Account"])
class LogoutAPIView(generics.CreateAPIView):
    """User logout - blacklist refresh token and clear session flag"""

    permission_classes = [permissions.IsAuthenticated]
    service = AuthService(account_repository=AccountRepository())

    def create(self, request, *args, **kwargs):
        self.service.logout_user(
            refresh_token=request.data.get("refresh"),
            user=request.user,
        )
        return Response(
            {"success": True, "message": "Logged out successfully"},
            status=status.HTTP_200_OK,
        )


def _emp_dict(emp):
    """Serialize a CustomUser into an employee dict."""
    from apps.accounts.models import USER_TYPES
    role = emp.user_type if emp.user_type in (
        USER_TYPES.OWNER, USER_TYPES.MANAGER, USER_TYPES.OPERATOR, USER_TYPES.ADMIN
    ) else ('owner' if emp.is_superuser else ('manager' if emp.is_staff else 'operator'))
    role_labels = {
        USER_TYPES.OWNER: 'Владелец',
        USER_TYPES.MANAGER: 'Менеджер',
        USER_TYPES.OPERATOR: 'Оператор',
        USER_TYPES.ADMIN: 'Администратор',
        'owner': 'Владелец',
        'manager': 'Менеджер',
        'operator': 'Оператор',
    }
    return {
        'id': emp.id,
        'username': emp.username,
        'full_name': f"{emp.first_name or ''} {emp.last_name or ''}".strip() or emp.username,
        'first_name': emp.first_name or '',
        'last_name': emp.last_name or '',
        'phone': str(getattr(emp, 'phone', '') or ''),
        'email': emp.email or '',
        'role': role,
        'role_display': role_labels.get(role, role),
        'created_at': (lambda d: d.strftime('%d.%m.%Y') if d else '')(getattr(emp, 'created_at', None) or getattr(emp, 'date_joined', None)),
    }


def _can_manage_staff(request):
    """Only club owner / manager / platform admin may create or modify staff.
    Prevents privilege escalation (any client setting role=owner)."""
    u = request.user
    if getattr(u, "user_type", "") == "admin":
        return True
    club_id = getattr(request, "current_club_id", None) or request.data.get("club") or request.query_params.get("club")
    if not club_id:
        return False
    try:
        from apps.clubs.models import Club, ClubMembership
        if Club.objects.filter(id=club_id, owner=u).exists():
            return True
        return ClubMembership.objects.filter(
            user=u, club_id=club_id, is_active=True, role__in=["owner", "manager"]
        ).exists()
    except Exception:
        return False


def _is_request_owner_of(requester, club_id, target):
    """Owner-protection: acting on the club OWNER is allowed only when the requester IS
    that club's owner. If the target isn't the owner, no extra restriction applies."""
    if not club_id:
        return True
    try:
        from apps.clubs.models import Club
        if not Club.objects.filter(id=club_id, owner=target).exists():
            return True
        return Club.objects.filter(id=club_id, owner=requester).exists()
    except Exception:
        return False


def _staff_target_in_club(emp, club_id):
    """SECURITY: the target employee must belong to the manager's OWN club. Staff
    endpoints fetched the target by global id with no scope, so a manager of club A
    could edit/delete — and privilege-escalate (role=owner → is_superuser) — staff or
    owners of club B. Platform admins bypass this (checked separately)."""
    if not club_id:
        return False
    try:
        from apps.clubs.models import Club, ClubMembership
        if Club.objects.filter(id=club_id, owner=emp).exists():
            return True
        return ClubMembership.objects.filter(user=emp, club_id=club_id, is_active=True).exists()
    except Exception:
        return False


class EmployeeListAPIView(APIView):
    """
    GET  /api/v1/accounts/employees/  – list staff for current club
    POST /api/v1/accounts/employees/  – create new staff account and link to club
      Body: {username, password, role, first_name?, last_name?, phone?}
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.accounts.models import CustomUser, USER_TYPES
        club_id = getattr(request, 'current_club_id', None) or request.query_params.get('club')

        if club_id:
            try:
                from apps.clubs.models import ClubMembership, Club
                # All members of this club via ClubMembership
                member_ids = set(
                    ClubMembership.objects.filter(club_id=club_id, is_active=True)
                    .values_list('user_id', flat=True)
                )
                # Always include the club owner even without a Membership record
                try:
                    owner_id = Club.objects.get(id=club_id).owner_id
                    member_ids.add(owner_id)
                except Club.DoesNotExist:
                    pass
                employees = CustomUser.objects.filter(id__in=member_ids).order_by('username')
            except Exception:
                employees = CustomUser.objects.filter(
                    user_type__in=[USER_TYPES.OWNER, USER_TYPES.MANAGER, USER_TYPES.OPERATOR, USER_TYPES.ADMIN]
                ).order_by('username')
        else:
            employees = CustomUser.objects.filter(
                user_type__in=[USER_TYPES.OWNER, USER_TYPES.MANAGER, USER_TYPES.OPERATOR, USER_TYPES.ADMIN]
            ).order_by('username')

        return Response([_emp_dict(e) for e in employees])

    def post(self, request):
        from apps.accounts.models import CustomUser, USER_TYPES
        if not _can_manage_staff(request):
            return Response({'error': 'Недостаточно прав для управления сотрудниками'}, status=status.HTTP_403_FORBIDDEN)
        club_id    = getattr(request, 'current_club_id', None) or request.data.get('club')
        username   = (request.data.get('username') or '').strip()
        password   = (request.data.get('password') or '').strip()
        role       = request.data.get('role', USER_TYPES.OPERATOR)
        first_name = (request.data.get('first_name') or '').strip()
        last_name  = (request.data.get('last_name')  or '').strip()
        phone      = (request.data.get('phone')      or '').strip()

        if not username:
            return Response({'error': 'Логин обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        if not password or len(password) < 6:
            return Response({'error': 'Пароль минимум 6 символов'}, status=status.HTTP_400_BAD_REQUEST)
        if CustomUser.objects.filter(username__iexact=username).exists():
            return Response({'error': 'Пользователь с таким логином уже существует'}, status=status.HTTP_400_BAD_REQUEST)
        # phone is unique=True — a duplicate raised an unhandled IntegrityError (500).
        if phone and CustomUser.objects.filter(phone=phone).exists():
            return Response({'error': 'Телефон уже занят'}, status=status.HTTP_400_BAD_REQUEST)

        # SECURITY: do NOT allow assigning user_type='admin' here — that is the
        # PLATFORM super-admin, which bypasses club isolation for ALL clubs. A club
        # owner/manager must only create club-scoped staff.
        valid_roles = [USER_TYPES.OWNER, USER_TYPES.MANAGER, USER_TYPES.OPERATOR]
        if role not in valid_roles:
            role = USER_TYPES.OPERATOR

        emp = CustomUser(
            username=username,
            first_name=first_name,
            last_name=last_name,
            user_type=role,
            is_staff=(role in [USER_TYPES.MANAGER, USER_TYPES.OWNER]),
            is_superuser=(role == USER_TYPES.OWNER),
        )
        if phone:
            emp.phone = phone
        emp.set_password(password)
        emp.save()

        # Link new employee to the current club via ClubMembership
        if club_id:
            try:
                from apps.clubs.models import ClubMembership
                # Map user_type role → ClubMembership.Role (admin→sysadmin fallback)
                valid_mb_roles = [r.value for r in ClubMembership.Role]
                mb_role = role if role in valid_mb_roles else 'operator'
                ClubMembership.objects.get_or_create(
                    user=emp, club_id=club_id,
                    defaults={'role': mb_role, 'is_active': True},
                )
            except Exception:
                pass  # Non-critical — employee created even if membership link fails

        try:
            from apps.billing.services.audit import log_action
            from apps.billing.models import LogAction
            log_action(
                request, LogAction.DB_CREATE, obj=emp, object_type="Employee",
                club_id=club_id,
                repr_=f"Сотрудник: {emp.username} ({role})",
                payload={"username": emp.username, "role": role},
            )
        except Exception:
            pass

        return Response(_emp_dict(emp), status=status.HTTP_201_CREATED)


class EmployeeManageAPIView(APIView):
    """
    PATCH  /api/v1/accounts/employees/<id>/ - update employee role/name
    DELETE /api/v1/accounts/employees/<id>/ - remove staff role
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        from apps.accounts.models import CustomUser, USER_TYPES
        if not _can_manage_staff(request):
            return Response({'error': 'Недостаточно прав для управления сотрудниками'}, status=status.HTTP_403_FORBIDDEN)
        try:
            emp = CustomUser.objects.get(id=pk)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

        # SECURITY: confirm the target belongs to the caller's club (unless platform admin).
        is_platform_admin = getattr(request.user, "user_type", "") == "admin"
        scope_club = getattr(request, 'current_club_id', None) or request.data.get('club') or request.query_params.get('club')
        if not is_platform_admin and not _staff_target_in_club(emp, scope_club):
            return Response({'error': 'Нет прав на этого сотрудника'}, status=status.HTTP_403_FORBIDDEN)
        # A mere manager must NOT be able to demote/strip the club OWNER. Only the owner
        # themselves or a platform admin may modify the owner.
        if not is_platform_admin and not _is_request_owner_of(request.user, scope_club, emp):
            return Response({'error': 'Только владелец клуба может изменять владельца'}, status=status.HTTP_403_FORBIDDEN)

        role = request.data.get('role', emp.user_type)
        if request.data.get('first_name') is not None:
            emp.first_name = request.data['first_name']
        if request.data.get('last_name') is not None:
            emp.last_name = request.data['last_name']

        # SECURITY: 'admin' (platform super-admin) is not assignable via staff mgmt.
        valid_roles = [USER_TYPES.OWNER, USER_TYPES.MANAGER, USER_TYPES.OPERATOR]
        if role in valid_roles:
            emp.user_type = role
            emp.is_staff = role in [USER_TYPES.MANAGER, USER_TYPES.OWNER]
            emp.is_superuser = (role == USER_TYPES.OWNER)

        emp.save(update_fields=['first_name', 'last_name', 'user_type', 'is_staff', 'is_superuser'])

        # Also sync ClubMembership.role for this club
        club_id = getattr(request, 'current_club_id', None) or request.data.get('club')
        if club_id:
            try:
                from apps.clubs.models import ClubMembership
                valid_mb_roles = [r.value for r in ClubMembership.Role]
                mb_role = role if role in valid_mb_roles else 'operator'
                ClubMembership.objects.filter(user=emp, club_id=club_id).update(role=mb_role)
            except Exception:
                pass

        try:
            from apps.billing.services.audit import log_action
            from apps.billing.models import LogAction
            log_action(
                request, LogAction.DB_UPDATE, obj=emp, object_type="Employee",
                club_id=club_id,
                repr_=f"Сотрудник изменён: {emp.username} ({role})",
                payload={"username": emp.username, "role": role},
            )
        except Exception:
            pass

        return Response(_emp_dict(emp))

    def delete(self, request, pk):
        from apps.accounts.models import CustomUser, USER_TYPES
        if not _can_manage_staff(request):
            return Response({'error': 'Недостаточно прав для управления сотрудниками'}, status=status.HTTP_403_FORBIDDEN)
        try:
            emp = CustomUser.objects.get(id=pk)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

        is_platform_admin = getattr(request.user, "user_type", "") == "admin"
        club_id = (
            getattr(request, 'current_club_id', None)
            or request.data.get('club')
            or request.query_params.get('club')
        )

        # SECURITY: a non-admin may only remove a target that belongs to their OWN club.
        # Was fetched by global id, and the "no club context" branch did a GLOBAL demotion
        # — letting a manager of one club demote/lock out another club's owner.
        if not is_platform_admin and not _staff_target_in_club(emp, club_id):
            return Response({'error': 'Нет прав на этого сотрудника'}, status=status.HTTP_403_FORBIDDEN)
        # A manager must not remove/demote the club OWNER — only the owner or admin.
        if not is_platform_admin and not _is_request_owner_of(request.user, club_id, emp):
            return Response({'error': 'Только владелец клуба может удалить владельца'}, status=status.HTTP_403_FORBIDDEN)

        if club_id:
            # Remove from this club only
            try:
                from apps.clubs.models import ClubMembership
                ClubMembership.objects.filter(user=emp, club_id=club_id).delete()
            except Exception:
                pass
            # Demote user_type only if they have no memberships left in any club
            try:
                from apps.clubs.models import ClubMembership
                if not ClubMembership.objects.filter(user=emp, is_active=True).exists():
                    emp.user_type = USER_TYPES.USER
                    emp.is_staff = False
                    emp.is_superuser = False
                    emp.save(update_fields=['user_type', 'is_staff', 'is_superuser'])
            except Exception:
                pass
        elif is_platform_admin:
            # No club context — global demotion is only for the platform admin.
            emp.user_type = USER_TYPES.USER
            emp.is_staff = False
            emp.is_superuser = False
            emp.save(update_fields=['user_type', 'is_staff', 'is_superuser'])
        else:
            return Response({'error': 'Не указан клуб'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.billing.services.audit import log_action
            from apps.billing.models import LogAction
            log_action(
                request, LogAction.DB_DELETE, obj=emp, object_type="Employee",
                club_id=club_id,
                repr_=f"Сотрудник удалён: {emp.username}",
                payload={"username": emp.username},
            )
        except Exception:
            pass

        return Response({'success': True})


class ClientCreateAPIView(APIView):
    """
    POST /api/v1/accounts/clients/
    Admin: register a new client account and link to the current club.

    Body: { username, phone?, first_name?, last_name?, email?, password? }
    - password defaults to username if omitted
    - auto-creates UserClubProfile for current club
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.accounts.models import CustomUser, USER_TYPES

        username   = (request.data.get('username') or '').strip()
        phone      = (request.data.get('phone')      or '').strip()
        first_name = (request.data.get('first_name') or '').strip()
        last_name  = (request.data.get('last_name')  or '').strip()
        email      = (request.data.get('email')      or '').strip()
        password   = (request.data.get('password')   or '').strip()
        club_id    = getattr(request, 'current_club_id', None) or request.data.get('club')

        # Setting gate: «Регистрация клиентов оператором». Platform admins bypass;
        # club operators are blocked when the club disabled this.
        is_platform_admin = getattr(request.user, "user_type", "") == "admin"
        if not is_platform_admin:
            from apps.clubs.models import ClubSettings
            if not ClubSettings.get_bool(club_id, "operator_client_registration", True):
                return Response(
                    {'error': 'Регистрация клиентов оператором отключена в настройках клуба'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if not username:
            return Response({'error': 'Логин обязателен'}, status=status.HTTP_400_BAD_REQUEST)

        # Default password = username; must be ≥6 chars
        if not password:
            password = username
        if len(password) < 6:
            return Response({'error': 'Пароль минимум 6 символов'}, status=status.HTTP_400_BAD_REQUEST)

        if CustomUser.objects.filter(username__iexact=username).exists():
            return Response({'error': 'Пользователь с таким логином уже существует'}, status=status.HTTP_400_BAD_REQUEST)

        if email and CustomUser.objects.filter(email__iexact=email).exists():
            return Response({'error': 'Email уже занят'}, status=status.HTTP_400_BAD_REQUEST)

        # phone is unique=True — a duplicate raised an unhandled IntegrityError (500).
        if phone and CustomUser.objects.filter(phone=phone).exists():
            return Response({'error': 'Телефон уже занят'}, status=status.HTTP_400_BAD_REQUEST)

        client = CustomUser(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            user_type=USER_TYPES.USER,
            is_staff=False,
            is_superuser=False,
        )
        if phone:
            try:
                client.phone = phone
            except Exception:
                pass  # phone format validation - best effort
        client.set_password(password)
        client.save()

        # Auto-create UserClubProfile for the current club
        if club_id:
            try:
                from apps.clubs.models import UserClubProfile
                UserClubProfile.objects.get_or_create(
                    user=client,
                    club_id=club_id,
                    defaults={'personal_discount': 0, 'is_blocked': False},
                )
            except Exception:
                pass  # non-critical
            # Fire REGISTRATION-trigger achievements (was never invoked anywhere, so
            # welcome/first-join achievements never unlocked for anyone).
            try:
                from apps.loyalty.services.achievements import evaluate_achievements
                evaluate_achievements(client, club_id, "registration")
            except Exception:
                pass

        return Response({
            'id': str(client.pk),
            'username': client.username,
            'phone': str(getattr(client, 'phone', None) or ''),
            'email': client.email or '',
            'full_name': f'{client.first_name} {client.last_name}'.strip(),
            'minutes_remaining': 0,
            'formatted_time': '0ч 0м',
            'is_active': False,
            'deposit_money': '0',
            'bonus_balance': '0',
            'personal_discount': 0,
            'is_blocked': False,
            'comment': '',
        }, status=status.HTTP_201_CREATED)


class UserSearchAPIView(APIView):
    """
    GET /api/v1/accounts/users/search/?q=<query>
    Search users by username, phone, or email.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.accounts.models import CustomUser
        from django.db.models import Q
        q = request.query_params.get('q', '').strip()
        if not q or len(q) < 2:
            return Response([])

        # SECURITY: was searching ALL users platform-wide → any authenticated user could
        # enumerate every club's clients (names, phones). Scope to clients of the caller's
        # own club (those with a UserClubProfile there).
        from apps.clubs.api.v1.mixins import validated_club_id
        from apps.clubs.models import UserClubProfile
        cid = validated_club_id(request)
        if not cid:
            return Response([])
        member_ids = UserClubProfile.objects.filter(club_id=cid).values_list('user_id', flat=True)
        users = CustomUser.objects.filter(
            (Q(username__icontains=q) | Q(email__icontains=q)) & Q(id__in=member_ids)
        )[:20]

        result = []
        for u in users:
            result.append({
                'id': u.id,
                'username': u.username,
                'full_name': f"{u.first_name or ''} {u.last_name or ''}".strip() or u.username,
                'phone': getattr(u, 'phone', '') or '',
            })
        return Response(result)
