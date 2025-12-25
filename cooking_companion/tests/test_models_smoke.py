from __future__ import annotations

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from cooking_companion.models import (
    CookResult,
    CookSession,
    Dish,
    Note,
    PDFDocument,
    Recipe,
    ReferenceURL,
)

pytestmark = pytest.mark.django_db


def make_user():
    User = get_user_model()
    return User.objects.create_user(username="tiny", password="pass12345")


def test_core_models_create():
    user = make_user()
    r = Recipe.objects.create(title="Oven Bacon", created_by=user)
    d = Dish.objects.create(name="Oven Bacon", default_recipe=r, created_by=user)
    s = CookSession.objects.create(dish=d, recipe_used=r, cooked_on=datetime.date.today(), created_by=user)
    res = CookResult.objects.create(cook_session=s, created_by=user)
    assert str(r)
    assert str(d)
    assert str(s)
    assert str(res)


def test_generic_attachments_attach_to_recipe():
    user = make_user()
    r = Recipe.objects.create(title="Test", created_by=user)
    ct = ContentType.objects.get_for_model(Recipe)

    n = Note.objects.create(content_type=ct, object_id=str(r.pk), title="Note", body="Hello", created_by=user)
    u = ReferenceURL.objects.create(content_type=ct, object_id=str(r.pk), url="https://example.com", created_by=user)
    p = PDFDocument.objects.create(content_type=ct, object_id=str(r.pk), created_by=user, pdf="fake.pdf")

    assert n.object_id == str(r.pk)
    assert u.object_id == str(r.pk)
    assert p.object_id == str(r.pk)
