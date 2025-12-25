from __future__ import annotations

from django import forms
from django.db.models import Q

from .models import CookResult, CookSession, Dish, Note, PDFDocument, Recipe, ReferenceURL, TrackedImage


def _owned_q(user):
    return Q(created_by=user) | Q(created_by__isnull=True)


def _apply_bootstrap(field: forms.Field):
    if isinstance(field.widget, (forms.CheckboxInput,)):
        field.widget.attrs.setdefault("class", "form-check-input")
    elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
        field.widget.attrs.setdefault("class", "form-select")
    else:
        field.widget.attrs.setdefault("class", "form-control")


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = [
            "title", "description", "author",
            "ingredients", "instructions",
            "yield_text", "prep_minutes", "cook_minutes",
            "is_favorite", "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "ingredients": forms.Textarea(attrs={"rows": 6}),
            "instructions": forms.Textarea(attrs={"rows": 8}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            _apply_bootstrap(field)


class DishForm(forms.ModelForm):
    class Meta:
        model = Dish
        fields = ["name", "description", "default_recipe", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            _apply_bootstrap(field)
        if user is not None:
            self.fields["default_recipe"].queryset = Recipe.objects.filter(_owned_q(user)).order_by("title")


class CookSessionForm(forms.ModelForm):
    class Meta:
        model = CookSession
        fields = [
            "dish", "recipe_used",
            "cooked_on", "meal_type", "method",
            "servings_made", "duration_minutes",
            "summary", "is_active",
        ]
        widgets = {
            "cooked_on": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            _apply_bootstrap(field)
        if user is not None:
            self.fields["dish"].queryset = Dish.objects.filter(_owned_q(user)).order_by("name")
            self.fields["recipe_used"].queryset = Recipe.objects.filter(_owned_q(user)).order_by("title")


class CookResultForm(forms.ModelForm):
    class Meta:
        model = CookResult
        fields = [
            "outcome",
            "overall_rating", "taste_rating", "texture_rating", "appearance_rating",
            "would_make_again",
            "what_worked", "what_to_change", "next_time_plan",
        ]
        widgets = {
            "what_worked": forms.Textarea(attrs={"rows": 4}),
            "what_to_change": forms.Textarea(attrs={"rows": 4}),
            "next_time_plan": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            _apply_bootstrap(field)


class NoteForTargetForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ["title", "body", "is_pinned"]
        widgets = {"body": forms.Textarea(attrs={"rows": 8})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            _apply_bootstrap(field)


class ReferenceURLForTargetForm(forms.ModelForm):
    class Meta:
        model = ReferenceURL
        fields = ["kind", "title", "url", "description", "sort_order", "is_primary"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            _apply_bootstrap(field)


class TrackedImageForTargetForm(forms.ModelForm):
    class Meta:
        model = TrackedImage
        fields = ["image", "caption", "alt_text", "taken_at", "sort_order", "is_cover"]
        widgets = {"taken_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            _apply_bootstrap(field)


class PDFDocumentForTargetForm(forms.ModelForm):
    class Meta:
        model = PDFDocument
        fields = ["kind", "title", "description", "pdf", "page_count", "sort_order"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            _apply_bootstrap(field)
