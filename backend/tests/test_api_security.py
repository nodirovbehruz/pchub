"""Auth / IDOR / tenant-isolation regression tests for audit fixes."""
import pytest


# ── GraphQL endpoint removed (was unauthenticated privilege escalation) ──────
@pytest.mark.django_db
def test_graphql_endpoint_is_gone(api):
    # /graphql/ let anyone promote themselves to platform admin via manageEmployee.
    # The route was removed entirely; it must no longer resolve.
    resp = api.post("/graphql/", {"query": "{__typename}"}, format="json")
    assert resp.status_code == 404


# ── client-groups: cross-tenant read/write via ?club= must be denied ─────────
@pytest.mark.django_db
def test_client_groups_cross_tenant_read_denied(api, make_club, make_user, make_membership):
    from apps.clubs.models import ClientGroup
    club_a = make_club()
    club_b = make_club()
    ClientGroup.objects.create(club=club_b, name="VIP-B", percent_discount=10)

    # A user who only belongs to club_a tries to read club_b's groups by passing ?club=B.
    outsider = make_user()
    make_membership(outsider, club_a, role="operator")
    api.force_authenticate(user=outsider)

    resp = api.get("/api/v1/clubs/client-groups/", {"club": club_b.id})
    assert resp.status_code == 200
    assert resp.json() == []  # must NOT see club_b's group

    # The legitimate owner of club_b DOES see it (sanity: not just always-empty).
    api.force_authenticate(user=club_b.owner)
    resp_b = api.get("/api/v1/clubs/client-groups/", {"club": club_b.id})
    assert resp_b.status_code == 200
    assert any(g["name"] == "VIP-B" for g in resp_b.json())


@pytest.mark.django_db
def test_client_groups_cross_tenant_create_denied(api, make_club, make_user, make_membership):
    from apps.clubs.models import ClientGroup
    club_a = make_club()
    club_b = make_club()
    outsider = make_user()
    make_membership(outsider, club_a, role="operator")
    api.force_authenticate(user=outsider)

    resp = api.post("/api/v1/clubs/client-groups/", {"name": "Hacked", "club": club_b.id},
                    format="json")
    assert resp.status_code == 403
    assert not ClientGroup.objects.filter(club=club_b, name="Hacked").exists()


# ── Club detail must not leak club_token to non-members ──────────────────────
@pytest.mark.django_db
def test_club_detail_hidden_from_non_member(api, make_club, make_user):
    club_b = make_club()
    outsider = make_user()
    api.force_authenticate(user=outsider)

    resp = api.get(f"/api/v1/clubs/{club_b.id}/")
    assert resp.status_code == 403  # was 200, leaking club_token + owner contacts

    # Owner can read it.
    api.force_authenticate(user=club_b.owner)
    ok = api.get(f"/api/v1/clubs/{club_b.id}/")
    assert ok.status_code == 200


# ── A manager must not be able to demote/remove the club OWNER ───────────────
@pytest.mark.django_db
def test_manager_cannot_demote_owner(api, make_club, make_user, make_membership):
    club = make_club()
    owner = club.owner
    manager = make_user()
    make_membership(manager, club, role="manager")
    api.force_authenticate(user=manager)

    resp = api.patch(f"/api/v1/accounts/employees/{owner.pk}/",
                     {"role": "operator", "club": club.id}, format="json")
    assert resp.status_code == 403

    owner.refresh_from_db()
    assert owner.user_type != "operator"  # role unchanged
