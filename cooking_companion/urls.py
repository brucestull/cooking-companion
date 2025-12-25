from __future__ import annotations

from django.urls import path

from . import views

app_name = "cooking_companion"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),

    path("recipes/", views.RecipeListView.as_view(), name="recipe-list"),
    path("recipes/add/", views.RecipeCreateView.as_view(), name="recipe-add"),
    path("recipes/<int:pk>/", views.RecipeDetailView.as_view(), name="recipe-detail"),
    path("recipes/<int:pk>/edit/", views.RecipeUpdateView.as_view(), name="recipe-edit"),
    path("recipes/<int:pk>/delete/", views.RecipeDeleteView.as_view(), name="recipe-delete"),

    path("dishes/", views.DishListView.as_view(), name="dish-list"),
    path("dishes/add/", views.DishCreateView.as_view(), name="dish-add"),
    path("dishes/<int:pk>/", views.DishDetailView.as_view(), name="dish-detail"),
    path("dishes/<int:pk>/edit/", views.DishUpdateView.as_view(), name="dish-edit"),
    path("dishes/<int:pk>/delete/", views.DishDeleteView.as_view(), name="dish-delete"),

    path("sessions/", views.CookSessionListView.as_view(), name="cooksession-list"),
    path("sessions/add/", views.CookSessionCreateView.as_view(), name="cooksession-add"),
    path("sessions/<int:pk>/", views.CookSessionDetailView.as_view(), name="cooksession-detail"),
    path("sessions/<int:pk>/edit/", views.CookSessionUpdateView.as_view(), name="cooksession-edit"),
    path("sessions/<int:pk>/delete/", views.CookSessionDeleteView.as_view(), name="cooksession-delete"),

    path("sessions/<int:session_pk>/result/edit/", views.CookResultCreateUpdateView.as_view(), name="cookresult-edit"),
    path("results/<int:pk>/", views.CookResultDetailView.as_view(), name="cookresult-detail"),

    path("target/<slug:model_key>/<int:pk>/", views.TargetDetailView.as_view(), name="target-detail"),
    path("target/<slug:model_key>/<int:pk>/notes/add/", views.TargetNoteCreateView.as_view(), name="target-note-add"),
    path("target/<slug:model_key>/<int:pk>/urls/add/", views.TargetReferenceURLCreateView.as_view(), name="target-url-add"),
    path("target/<slug:model_key>/<int:pk>/images/add/", views.TargetTrackedImageCreateView.as_view(), name="target-image-add"),
    path("target/<slug:model_key>/<int:pk>/pdfs/add/", views.TargetPDFDocumentCreateView.as_view(), name="target-pdf-add"),
]
