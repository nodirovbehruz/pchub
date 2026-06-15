"""Game group (Category) management — SmartShell-style 'Управление группами'."""
from django.utils.text import slugify
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.games.models.game import Category, Game


def _serialize(cat):
    return {
        "id": cat.id,
        "name": cat.name,
        "slug": cat.slug,
        "order": cat.order,
        "games_count": Game.objects.filter(category=cat).count(),
    }


class GameCategoryListCreateAPIView(APIView):
    """GET list groups · POST create a new group."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cats = Category.objects.all().order_by("order", "name")
        return Response([_serialize(c) for c in cats])

    def post(self, request):
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"error": "Название обязательно"}, status=status.HTTP_400_BAD_REQUEST)

        base = slugify(name, allow_unicode=False) or "group"
        slug = base
        i = 1
        while Category.objects.filter(slug=slug).exists():
            i += 1
            slug = f"{base}-{i}"

        order = request.data.get("order")
        if order is None:
            order = Category.objects.count()

        cat = Category.objects.create(name=name, slug=slug, order=order)
        return Response(_serialize(cat), status=status.HTTP_201_CREATED)


class GameCategoryDetailAPIView(APIView):
    """PATCH rename · DELETE (only if empty)."""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            cat = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response({"error": "Группа не найдена"}, status=status.HTTP_404_NOT_FOUND)

        if "name" in request.data:
            name = (request.data.get("name") or "").strip()
            if name:
                cat.name = name
        if "order" in request.data:
            try:
                cat.order = int(request.data["order"])
            except (TypeError, ValueError):
                pass
        cat.save(update_fields=["name", "order"])
        return Response(_serialize(cat))

    def delete(self, request, pk):
        try:
            cat = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response({"error": "Группа не найдена"}, status=status.HTTP_404_NOT_FOUND)

        count = Game.objects.filter(category=cat).count()
        if count > 0:
            return Response(
                {"error": f"Нельзя удалить группу — в ней {count} игр. Сначала перенесите игры."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cat.delete()
        return Response({"success": True})


class GameCategoryReorderAPIView(APIView):
    """POST { order: [id1, id2, ...] } — persist drag-and-drop order."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ids = request.data.get("order", [])
        if not isinstance(ids, list):
            return Response({"error": "order must be a list"}, status=status.HTTP_400_BAD_REQUEST)
        for idx, cid in enumerate(ids):
            Category.objects.filter(pk=cid).update(order=idx)
        return Response({"success": True})
