from django.urls import path
from rest_framework import generics, permissions, serializers as drf_serializers

from apps.clubs.api.v1.mixins import TenantFilterMixin, TenantCreateMixin
from apps.content.models import News, Task


class TaskSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"
        # `club` is read-only: it's forced by TenantCreateMixin on create, and leaving it
        # writable let an operator PATCH {club: <other>} to move the task into a foreign club.
        read_only_fields = ["id", "created_at", "updated_at", "finished_at", "finished_by", "club"]


class NewsSerializer(drf_serializers.ModelSerializer):
    cover_image_url = drf_serializers.SerializerMethodField()

    class Meta:
        model = News
        fields = "__all__"
        # `club` read-only — forced on create, must not be reassignable via PATCH.
        read_only_fields = ["id", "created_at", "updated_at", "cover_image_url", "club"]

    def get_cover_image_url(self, obj):
        if obj.cover_image:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.cover_image.url) if request else obj.cover_image.url
        return f"https://picsum.photos/seed/news-{obj.id}/624/352"

    def validate_cover_image(self, value):
        # The field documents «≤640 КБ, .jpg/.png» but had no validators — an operator
        # could upload a huge or wrong-format file (disk bloat, broken shell layout).
        if value:
            if getattr(value, "size", 0) > 640 * 1024:
                raise drf_serializers.ValidationError("Обложка должна быть не больше 640 КБ")
            name = (getattr(value, "name", "") or "").lower()
            if not name.endswith((".jpg", ".jpeg", ".png")):
                raise drf_serializers.ValidationError("Только формат .jpg или .png")
        return value

    def validate(self, attrs):
        # A reversed window (show_until < show_from) silently makes the news permanently
        # invisible (the published filter needs show_from<=now<=show_until) — reject it.
        sf = attrs.get("show_from", getattr(self.instance, "show_from", None))
        su = attrs.get("show_until", getattr(self.instance, "show_until", None))
        if sf and su and su < sf:
            raise drf_serializers.ValidationError(
                {"show_until": "Дата окончания показа раньше даты начала"})
        return attrs


class TaskListCreateAPIView(TenantCreateMixin, TenantFilterMixin, generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Task.objects.all()

    def get_queryset(self):
        # Filters (?is_finished, ?assigned_to, ?search) were silently ignored — the UI
        # offered them but the list never narrowed. Apply them on top of the tenant scope.
        import uuid as _uuid
        from django.db.models import Q
        qs = super().get_queryset()
        p = self.request.query_params
        fin = (p.get("is_finished") or "").lower()
        if fin in ("1", "true"):
            qs = qs.filter(is_finished=True)
        elif fin in ("0", "false"):
            qs = qs.filter(is_finished=False)
        if p.get("assigned_to"):
            try:
                qs = qs.filter(assigned_to_id=_uuid.UUID(str(p.get("assigned_to"))))
            except (ValueError, TypeError):
                pass
        if p.get("search"):
            s = p.get("search")
            qs = qs.filter(Q(title__icontains=s) | Q(body__icontains=s))
        return qs

    def tenant_create_extra(self):
        return {"created_by": self.request.user}


class TaskDetailAPIView(TenantFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Task.objects.all()

    def perform_update(self, serializer):
        # finished_at/finished_by are read-only to the client and were NEVER set, so the
        # dashboard's "Завершённые задачи" (ordered by -finished_at) showed all-NULL.
        # Stamp them server-side on the False→True transition (and clear on reopen).
        from django.utils import timezone
        was_finished = self.get_object().is_finished
        obj = serializer.save()
        if obj.is_finished and not was_finished:
            obj.finished_at = timezone.now()
            obj.finished_by = self.request.user
            obj.save(update_fields=["finished_at", "finished_by"])
        elif not obj.is_finished and was_finished:
            obj.finished_at = None
            obj.finished_by = None
            obj.save(update_fields=["finished_at", "finished_by"])


class NewsListCreateAPIView(TenantCreateMixin, TenantFilterMixin, generics.ListCreateAPIView):
    serializer_class = NewsSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = News.objects.all()

    def get_queryset(self):
        # Operators (owner/member/admin) see ALL of their club's news (incl. drafts).
        # Shell CLIENTS are not ClubMembers, so the default tenant filter returned
        # none() — give them their club's currently-published news (resolved from
        # ?club=/X-Club-Id) honoring the show_from/show_until display window (#14).
        from django.db.models import Q
        from django.utils import timezone
        from apps.clubs.api.v1.mixins import validated_club_id
        cid = validated_club_id(self.request)
        if cid:
            return News.objects.filter(club_id=cid)
        raw = (getattr(self.request, "current_club_id", None)
               or self.request.query_params.get("club")
               or self.request.META.get("HTTP_X_CLUB_ID"))
        try:
            raw = int(raw)
        except (TypeError, ValueError):
            return News.objects.none()
        now = timezone.now()
        return (News.objects.filter(club_id=raw, is_published=True)
                .filter(Q(show_from__isnull=True) | Q(show_from__lte=now))
                .filter(Q(show_until__isnull=True) | Q(show_until__gte=now)))


class NewsDetailAPIView(TenantFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = NewsSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = News.objects.all()


app_name = "content"

urlpatterns = [
    path("tasks/", TaskListCreateAPIView.as_view(), name="task-list"),
    path("tasks/<int:pk>/", TaskDetailAPIView.as_view(), name="task-detail"),
    path("news/", NewsListCreateAPIView.as_view(), name="news-list"),
    path("news/<int:pk>/", NewsDetailAPIView.as_view(), name="news-detail"),
]
