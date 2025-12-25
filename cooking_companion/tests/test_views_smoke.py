from __future__ import annotations

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from cooking_companion.models import CookSession, Dish, Recipe

pytestmark = pytest.mark.django_db


def login(client):
    User = get_user_model()
    user = User.objects.create_user(username="tiny", password="pass12345")
    assert client.login(username="tiny", password="pass12345")
    return user


def test_dashboard_loads(client):
    login(client)
    resp = client.get(reverse("cooking_companion:dashboard"))
    assert resp.status_code == 200


def test_recipe_crud_smoke(client):
    login(client)
    resp = client.post(reverse("cooking_companion:recipe-add"), data={"title": "R1"})
    assert resp.status_code in (302, 303)

    resp = client.get(reverse("cooking_companion:recipe-list"))
    assert resp.status_code == 200
    assert b"R1" in resp.content


def test_cooksession_create_smoke(client):
    user = login(client)
    r = Recipe.objects.create(title="R", created_by=user)
    d = Dish.objects.create(name="D", created_by=user)

    resp = client.post(
        reverse("cooking_companion:cooksession-add"),
        data={
            "dish": d.pk,
            "recipe_used": r.pk,
            "cooked_on": datetime.date.today().isoformat(),
            "meal_type": "other",
            "method": "other",
            "summary": "hi",
            "is_active": True,
        },
    )
    assert resp.status_code in (302, 303)
    assert CookSession.objects.count() == 1
