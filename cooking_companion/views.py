\
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import generic

from .forms import (
    CookResultForm,
    CookSessionForm,
    DishForm,
    NoteForTargetForm,
    PDFDocumentForTargetForm,
    RecipeForm,
    ReferenceURLForTargetForm,
    TrackedImageForTargetForm,
)
from .models import CookResult, CookSession, Dish, Note, PDFDocument, Recipe, ReferenceURL, TrackedImage


def owned_q(user):
    return Q(created_by=user) | Q(created_by__isnull=True)


class OwnedQuerysetMixin(LoginRequiredMixin):
    owner_field_name = "created_by"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(owned_q(self.request.user))

    def form_valid(self, form):
        obj = form.save(commit=False)
        if getattr(obj, f"{self.owner_field_name}_id", None) is None:
            setattr(obj, self.owner_field_name, self.request.user)
        obj.save()
        form.save_m2m()
        return redirect(self.get_success_url())


# ----------------------------
# Dashboard
# ----------------------------

@dataclass(frozen=True)
class Bucket:
    label: str
    count: int
    url: str


class DashboardView(LoginRequiredMixin, generic.TemplateView):
    template_name = "cooking_companion/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        user = self.request.user
        today = timezone.localdate()
        week_from_now = today + timedelta(days=7)
        month_from_now = today + timedelta(days=30)

        recipe_qs = Recipe.objects.filter(owned_q(user)).order_by("-updated_at")
        dish_qs = Dish.objects.filter(owned_q(user)).order_by("name")
        session_qs = CookSession.objects.filter(owned_q(user)).select_related("dish", "recipe_used").order_by("-cooked_on", "-created_at")

        ctx["counts"] = {
            "recipes": recipe_qs.count(),
            "dishes": dish_qs.count(),
            "sessions": session_qs.count(),
            "results": CookResult.objects.filter(owned_q(user)).count(),
            "images": TrackedImage.objects.filter(owned_q(user)).count(),
            "notes": Note.objects.filter(owned_q(user)).count(),
            "urls": ReferenceURL.objects.filter(owned_q(user)).count(),
            "pdfs": PDFDocument.objects.filter(owned_q(user)).count(),
        }

        ctx["recent_sessions"] = session_qs[:10]
        ctx["recent_recipes"] = recipe_qs[:8]
        ctx["popular_dishes"] = (
            dish_qs.annotate(session_count=Count("cook_sessions"))
            .order_by("-session_count", "name")[:8]
        )

        ctx["session_buckets"] = [
            Bucket("Today", session_qs.filter(cooked_on=today).count(), reverse("cooking_companion:cooksession-list") + "?when=today"),
            Bucket("Next 7 days", session_qs.filter(cooked_on__gt=today, cooked_on__lte=week_from_now).count(), reverse("cooking_companion:cooksession-list") + "?when=week"),
            Bucket("Next 30 days", session_qs.filter(cooked_on__gt=today, cooked_on__lte=month_from_now).count(), reverse("cooking_companion:cooksession-list") + "?when=month"),
            Bucket("Past 30 days", session_qs.filter(cooked_on__gte=today - timedelta(days=30), cooked_on__lte=today).count(), reverse("cooking_companion:cooksession-list") + "?when=past30"),
        ]

        ctx["top_outcomes"] = (
            CookResult.objects.filter(owned_q(user))
            .values("outcome")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        return ctx


# ----------------------------
# Recipes
# ----------------------------

class RecipeListView(LoginRequiredMixin, generic.ListView):
    model = Recipe
    paginate_by = 20
    template_name = "cooking_companion/recipe_list.html"

    def get_queryset(self):
        qs = Recipe.objects.filter(owned_q(self.request.user)).order_by("-updated_at", "title")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(author__icontains=q) | Q(description__icontains=q))
        if self.request.GET.get("favorite") == "1":
            qs = qs.filter(is_favorite=True)
        if self.request.GET.get("active") == "0":
            qs = qs.filter(is_active=False)
        return qs


class RecipeDetailView(LoginRequiredMixin, generic.DetailView):
    model = Recipe
    template_name = "cooking_companion/recipe_detail.html"

    def get_queryset(self):
        return Recipe.objects.filter(owned_q(self.request.user))


class RecipeCreateView(OwnedQuerysetMixin, generic.CreateView):
    model = Recipe
    form_class = RecipeForm
    template_name = "cooking_companion/form.html"

    def get_success_url(self):
        return reverse("cooking_companion:recipe-detail", kwargs={"pk": self.object.pk})


class RecipeUpdateView(OwnedQuerysetMixin, generic.UpdateView):
    model = Recipe
    form_class = RecipeForm
    template_name = "cooking_companion/form.html"

    def get_success_url(self):
        return reverse("cooking_companion:recipe-detail", kwargs={"pk": self.object.pk})


class RecipeDeleteView(OwnedQuerysetMixin, generic.DeleteView):
    model = Recipe
    template_name = "cooking_companion/confirm_delete.html"
    success_url = reverse_lazy("cooking_companion:recipe-list")


# ----------------------------
# Dishes
# ----------------------------

class DishListView(LoginRequiredMixin, generic.ListView):
    model = Dish
    paginate_by = 20
    template_name = "cooking_companion/dish_list.html"

    def get_queryset(self):
        qs = Dish.objects.filter(owned_q(self.request.user)).select_related("default_recipe")
        qs = qs.annotate(session_count=Count("cook_sessions")).order_by("name")

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(default_recipe__title__icontains=q))
        if self.request.GET.get("active") == "0":
            qs = qs.filter(is_active=False)
        return qs


class DishDetailView(LoginRequiredMixin, generic.DetailView):
    model = Dish
    template_name = "cooking_companion/dish_detail.html"

    def get_queryset(self):
        return Dish.objects.filter(owned_q(self.request.user)).select_related("default_recipe").annotate(session_count=Count("cook_sessions"))


class DishCreateView(OwnedQuerysetMixin, generic.CreateView):
    model = Dish
    form_class = DishForm
    template_name = "cooking_companion/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("cooking_companion:dish-detail", kwargs={"pk": self.object.pk})


class DishUpdateView(OwnedQuerysetMixin, generic.UpdateView):
    model = Dish
    form_class = DishForm
    template_name = "cooking_companion/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("cooking_companion:dish-detail", kwargs={"pk": self.object.pk})


class DishDeleteView(OwnedQuerysetMixin, generic.DeleteView):
    model = Dish
    template_name = "cooking_companion/confirm_delete.html"
    success_url = reverse_lazy("cooking_companion:dish-list")


# ----------------------------
# Cook Sessions + Results
# ----------------------------

class CookSessionListView(LoginRequiredMixin, generic.ListView):
    model = CookSession
    paginate_by = 25
    template_name = "cooking_companion/cooksession_list.html"

    def get_queryset(self):
        qs = (
            CookSession.objects.filter(owned_q(self.request.user))
            .select_related("dish", "recipe_used")
            .order_by("-cooked_on", "-created_at")
        )

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(dish__name__icontains=q) | Q(recipe_used__title__icontains=q) | Q(summary__icontains=q))

        when = self.request.GET.get("when")
        today = timezone.localdate()
        if when == "today":
            qs = qs.filter(cooked_on=today)
        elif when == "week":
            qs = qs.filter(cooked_on__gt=today, cooked_on__lte=today + timedelta(days=7))
        elif when == "month":
            qs = qs.filter(cooked_on__gt=today, cooked_on__lte=today + timedelta(days=30))
        elif when == "past30":
            qs = qs.filter(cooked_on__gte=today - timedelta(days=30), cooked_on__lte=today)

        meal = self.request.GET.get("meal_type")
        if meal:
            qs = qs.filter(meal_type=meal)

        method = self.request.GET.get("method")
        if method:
            qs = qs.filter(method=method)

        return qs


class CookSessionDetailView(LoginRequiredMixin, generic.DetailView):
    model = CookSession
    template_name = "cooking_companion/cooksession_detail.html"

    def get_queryset(self):
        return CookSession.objects.filter(owned_q(self.request.user)).select_related("dish", "recipe_used")


class CookSessionCreateView(OwnedQuerysetMixin, generic.CreateView):
    model = CookSession
    form_class = CookSessionForm
    template_name = "cooking_companion/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        dish_id = self.request.GET.get("dish")
        if dish_id:
            initial["dish"] = dish_id
        return initial

    def get_success_url(self):
        return reverse("cooking_companion:cooksession-detail", kwargs={"pk": self.object.pk})


class CookSessionUpdateView(OwnedQuerysetMixin, generic.UpdateView):
    model = CookSession
    form_class = CookSessionForm
    template_name = "cooking_companion/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("cooking_companion:cooksession-detail", kwargs={"pk": self.object.pk})


class CookSessionDeleteView(OwnedQuerysetMixin, generic.DeleteView):
    model = CookSession
    template_name = "cooking_companion/confirm_delete.html"
    success_url = reverse_lazy("cooking_companion:cooksession-list")


class CookResultCreateUpdateView(LoginRequiredMixin, generic.UpdateView):
    """
    Edit the CookResult for a CookSession.

    If the result doesn't exist, create it first then redirect into UpdateView.
    """
    model = CookResult
    form_class = CookResultForm
    template_name = "cooking_companion/form.html"

    def dispatch(self, request, *args, **kwargs):
        session_pk = kwargs.get("session_pk")
        cook_session = get_object_or_404(CookSession.objects.filter(owned_q(request.user)), pk=session_pk)
        obj, _created = CookResult.objects.get_or_create(
            cook_session=cook_session,
            defaults={"created_by": request.user},
        )
        self._obj = obj
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self._obj

    def get_success_url(self):
        return reverse("cooking_companion:cooksession-detail", kwargs={"pk": self.object.cook_session.pk})


class CookResultDetailView(LoginRequiredMixin, generic.DetailView):
    model = CookResult
    template_name = "cooking_companion/cookresult_detail.html"

    def get_queryset(self):
        return CookResult.objects.filter(owned_q(self.request.user)).select_related("cook_session", "cook_session__dish")


# ----------------------------
# Generic "attachments" UI
# ----------------------------

ALLOWED_TARGET_MODELS = {
    "recipe": Recipe,
    "dish": Dish,
    "cooksession": CookSession,
    "cookresult": CookResult,
}


def _get_target_or_404(user, model_key: str, pk: int):
    model = ALLOWED_TARGET_MODELS.get(model_key)
    if not model:
        raise Http404("Unknown target model")
    return get_object_or_404(model.objects.filter(owned_q(user)), pk=pk)


class TargetContextMixin(LoginRequiredMixin):
    target_model_key_url_kwarg = "model_key"
    target_pk_url_kwarg = "pk"

    def dispatch(self, request, *args, **kwargs):
        self.model_key = kwargs.get(self.target_model_key_url_kwarg)
        self.target_pk = kwargs.get(self.target_pk_url_kwarg)
        self.target_obj = _get_target_or_404(request.user, self.model_key, self.target_pk)
        self.target_ct = ContentType.objects.get_for_model(self.target_obj.__class__)
        return super().dispatch(request, *args, **kwargs)


class TargetNoteCreateView(TargetContextMixin, generic.CreateView):
    model = Note
    form_class = NoteForTargetForm
    template_name = "cooking_companion/form.html"

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.content_type = self.target_ct
        obj.object_id = str(self.target_obj.pk)
        if not obj.created_by_id:
            obj.created_by = self.request.user
        obj.save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("cooking_companion:target-detail", kwargs={"model_key": self.model_key, "pk": self.target_obj.pk})


class TargetReferenceURLCreateView(TargetContextMixin, generic.CreateView):
    model = ReferenceURL
    form_class = ReferenceURLForTargetForm
    template_name = "cooking_companion/form.html"

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.content_type = self.target_ct
        obj.object_id = str(self.target_obj.pk)
        if not obj.created_by_id:
            obj.created_by = self.request.user
        obj.save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("cooking_companion:target-detail", kwargs={"model_key": self.model_key, "pk": self.target_obj.pk})


class TargetTrackedImageCreateView(TargetContextMixin, generic.CreateView):
    model = TrackedImage
    form_class = TrackedImageForTargetForm
    template_name = "cooking_companion/form.html"

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.content_type = self.target_ct
        obj.object_id = str(self.target_obj.pk)
        if not obj.created_by_id:
            obj.created_by = self.request.user
        obj.save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("cooking_companion:target-detail", kwargs={"model_key": self.model_key, "pk": self.target_obj.pk})


class TargetPDFDocumentCreateView(TargetContextMixin, generic.CreateView):
    model = PDFDocument
    form_class = PDFDocumentForTargetForm
    template_name = "cooking_companion/form.html"

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.content_type = self.target_ct
        obj.object_id = str(self.target_obj.pk)
        if not obj.created_by_id:
            obj.created_by = self.request.user
        obj.save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("cooking_companion:target-detail", kwargs={"model_key": self.model_key, "pk": self.target_obj.pk})


class TargetDetailView(TargetContextMixin, generic.TemplateView):
    template_name = "cooking_companion/target_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ct = self.target_ct
        oid = str(self.target_obj.pk)
        user = self.request.user

        ctx["target_model_key"] = self.model_key
        ctx["target_obj"] = self.target_obj

        ctx["notes"] = Note.objects.filter(content_type=ct, object_id=oid).filter(owned_q(user)).order_by("-is_pinned", "-updated_at")
        ctx["urls"] = ReferenceURL.objects.filter(content_type=ct, object_id=oid).filter(owned_q(user)).order_by("sort_order", "-created_at")
        ctx["images"] = TrackedImage.objects.filter(content_type=ct, object_id=oid).filter(owned_q(user)).order_by("sort_order", "-created_at")
        ctx["pdfs"] = PDFDocument.objects.filter(content_type=ct, object_id=oid).filter(owned_q(user)).order_by("sort_order", "-created_at")

        ctx["add_note_url"] = reverse("cooking_companion:target-note-add", kwargs={"model_key": self.model_key, "pk": self.target_obj.pk})
        ctx["add_url_url"] = reverse("cooking_companion:target-url-add", kwargs={"model_key": self.model_key, "pk": self.target_obj.pk})
        ctx["add_image_url"] = reverse("cooking_companion:target-image-add", kwargs={"model_key": self.model_key, "pk": self.target_obj.pk})
        ctx["add_pdf_url"] = reverse("cooking_companion:target-pdf-add", kwargs={"model_key": self.model_key, "pk": self.target_obj.pk})

        return ctx
