import graphene
from django.db.models import Q
from apps.accounts.models import CustomUser, USER_TYPES
from apps.accounts.models.enums import UserType

class EmployeeType(graphene.ObjectType):
    id = graphene.ID()
    username = graphene.String()
    full_name = graphene.String()
    phone = graphene.String()
    email = graphene.String()
    role = graphene.String()
    role_display = graphene.String()
    created_at = graphene.String()

class UserSearchResultType(graphene.ObjectType):
    id = graphene.ID()
    username = graphene.String()
    phone = graphene.String()
    full_name = graphene.String()

class Query(graphene.ObjectType):
    employees = graphene.List(EmployeeType)
    search_users_by_phone = graphene.List(UserSearchResultType, last_digits=graphene.String(required=True))

    def resolve_employees(self, info):
        # Employees are anyone not 'user'
        staff = CustomUser.objects.exclude(user_type=UserType.USER).order_by('user_type', 'username')
        result = []
        for s in staff:
            result.append(EmployeeType(
                id=str(s.id),
                username=s.username,
                full_name=s.get_full_name() or s.username,
                phone=str(s.phone) if s.phone else '—',
                email=s.email or '—',
                role=s.user_type,
                role_display=s.get_user_type_display(),
                created_at=s.created_at.strftime('%d.%m.%Y')
            ))
        return result

    def resolve_search_users_by_phone(self, info, last_digits):
        # Users registered in shell usually have a phone.
        # SmartShell search: last 4 digits
        users = CustomUser.objects.filter(phone__endswith=last_digits).exclude(user_type__in=[UserType.OWNER, UserType.MANAGER, UserType.OPERATOR])[:10]
        return [UserSearchResultType(
            id=str(u.id),
            username=u.username,
            phone=str(u.phone),
            full_name=u.get_full_name()
        ) for u in users]

class ManageEmployeeMutation(graphene.Mutation):
    class Arguments:
        user_id = graphene.ID(required=True)
        role = graphene.String(required=True)
        first_name = graphene.String()
        last_name = graphene.String()

    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, user_id, role, first_name=None, last_name=None):
        try:
            user = CustomUser.objects.get(id=user_id)
            user.user_type = role
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name
            user.is_staff = True # Ensure they can access admin features if needed
            user.save()
            return ManageEmployeeMutation(success=True, message=f"Сотрудник {user.username} обновлен")
        except CustomUser.DoesNotExist:
            return ManageEmployeeMutation(success=False, message="Пользователь не найден")

class RemoveEmployeeMutation(graphene.Mutation):
    class Arguments:
        user_id = graphene.ID(required=True)

    success = graphene.Boolean()

    def mutate(self, info, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            user.user_type = UserType.USER
            # user.is_staff = False # Optionally remove staff status
            user.save()
            return RemoveEmployeeMutation(success=True)
        except CustomUser.DoesNotExist:
            return RemoveEmployeeMutation(success=False)

class Mutation(graphene.ObjectType):
    manage_employee = ManageEmployeeMutation.Field()
    remove_employee = RemoveEmployeeMutation.Field()
