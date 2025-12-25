# Cooking Companion (reusable Django app)

A reusable Django app you can install into another Django project (e.g. your "Personal Assistant") to track:

- Recipes
- Dishes
- Cook sessions
- Cook results
- Notes, images, reference URLs, and PDFs attached to any object via GenericForeignKey

## Quick start (in your host Django project)

### 1) Install (editable, local dev)
```bash
pip install -e ../cooking-companion
# or with pipenv in the host project
pipenv install -e ../cooking-companion
```

### 2) Add to `INSTALLED_APPS`
```python
INSTALLED_APPS = [
    # ...
    "django.contrib.contenttypes",  # required for generic relations (usually already enabled)
    "cooking_companion.apps.CookingCompanionConfig",
]
```

### 3) Include URLs (optional, for the dashboard + CRUD UI)
```python
from django.urls import include, path

urlpatterns = [
    # ...
    path("cooking/", include("cooking_companion.urls")),
]
```

### 4) Migrations
Generate migrations in the app once while in editable mode:

```bash
python manage.py makemigrations cooking_companion
python manage.py migrate
```

## Notes

- Templates extend `base.html`. Your host project probably already has one.
- Bootstrap 5 is assumed to be available in the host project's base template.
- Image uploads require Pillow (included as a dependency).
