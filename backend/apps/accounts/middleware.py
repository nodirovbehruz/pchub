from django.utils import timezone

class UpdateLastActivityMiddleware:
    """
    Middleware that updates the last_activity field for authenticated users.
    To avoid excessive DB writes, it only updates once per minute.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now = timezone.now()
            # Only update if last_activity is older than 60 seconds or not set
            if not request.user.last_activity or (now - request.user.last_activity).total_seconds() > 30:
                # Update every 30s — matches client heartbeat interval
                from apps.accounts.models import CustomUser
                CustomUser.objects.filter(id=request.user.id).update(last_activity=now)
                request.user.last_activity = now
        
        response = self.get_response(request)
        return response


class GrapheneJWTAuthenticationMiddleware:
    def resolve(self, next, root, info, **args):
        request = info.context
        
        # Only authenticate if user is not already authenticated by session
        if hasattr(request, 'user') and not request.user.is_authenticated:
            try:
                from rest_framework_simplejwt.authentication import JWTAuthentication
                auth = JWTAuthentication()
                user_auth_tuple = auth.authenticate(request)
                if user_auth_tuple is not None:
                    request.user, request.auth = user_auth_tuple
            except Exception:
                pass
                
        return next(root, info, **args)
