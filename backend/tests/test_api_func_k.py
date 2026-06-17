"""Regression: toggling high-access creates the ShellSecurity row so the club's default
high-access password ('pasw0rd') is actually sent — it was empty (row never created)."""
import pytest


@pytest.mark.django_db
def test_high_access_uses_default_password(api, make_club):
    from apps.computers.models import Computer
    from apps.integrations.models.shell_security import ShellSecurity
    club = make_club()
    pc = Computer.objects.create(name="PC-ha", club=club)
    assert not ShellSecurity.objects.filter(club=club).exists()

    api.force_authenticate(user=club.owner)
    resp = api.post(f"/api/v1/computers/{pc.id}/high-access/", {"enabled": True}, format="json")
    assert resp.status_code in (200, 201), resp.content

    sec = ShellSecurity.objects.filter(club=club).first()
    assert sec is not None                          # row now created
    assert sec.high_access_password == "pasw0rd"    # model default applied (was empty)
