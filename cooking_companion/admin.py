from __future__ import annotations

from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.db.models import Count
from django.utils.html import format_html

from .models import (
    CookResult,
    CookSession,
    Dish,
    Note,
    PDFDocument,
    Recipe,
    ReferenceURL,
    TrackedImage,
)


class NoteInline(GenericTabularInline):
    model = Note
    extra = 0
    fields = ("is_pinned", "title", "body", "created_by", "updated_at")
    readonly_fields = ("created_by", "updated_at")
    show_change_link = True

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for inst in instances:
            if getattr(inst, "created_by_id", None) is None:
                inst.created_by = request.user
            inst.save()
        formset.save_m2m()


class TrackedImageInline(GenericTabularInline):
    model = TrackedImage
    extra = 0
    fields = ("thumb", "image", "is_cover", "sort_order", "caption", "alt_text", "taken_at", "created_by")
    readonly_fields = ("thumb", "created_by")
    show_change_link = True

    def thumb(self, obj: TrackedImage):
        if not obj.pk or not obj.image:
            return "-"
        try:
            return format_html('<img src="{}" style="height:40px; width:auto; border-radius:6px;" />', obj.image.url)
        except Exception:
            return "image"

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for inst in instances:
            if getattr(inst, "created_by_id", None) is None:
                inst.created_by = request.user
            inst.save()
        formset.save_m2m()


class ReferenceURLInline(GenericTabularInline):
    model = ReferenceURL
    extra = 0
    fields = ("is_primary", "kind", "title", "url", "sort_order", "created_by")
    readonly_fields = ("created_by",)
    show_change_link = True

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for inst in instances:
            if getattr(inst, "created_by_id", None) is None:
                inst.created_by = request.user
            inst.save()
        formset.save_m2m()


class PDFDocumentInline(GenericTabularInline):
    model = PDFDocument
    extra = 0
    fields = ("kind", "title", "pdf", "original_filename", "sort_order", "created_by")
    readonly_fields = ("original_filename", "created_by")
    show_change_link = True

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for inst in instances:
            if getattr(inst, "created_by_id", None) is None:
                inst.created_by = request.user
            inst.save()
        formset.save_m2m()


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "is_favorite", "is_active", "updated_at", "created_by")
    list_filter = ("is_favorite", "is_active", "created_at", "updated_at")
    search_fields = ("title", "author", "description", "ingredients")
    readonly_fields = ("created_at", "updated_at")
    inlines = (ReferenceURLInline, PDFDocumentInline, NoteInline, TrackedImageInline)
    fieldsets = (
        (None, {"fields": ("title", "author", "description", "is_favorite", "is_active")}),
        ("Content", {"fields": ("ingredients", "instructions")}),
        ("Timing / Yield", {"fields": ("yield_text", "prep_minutes", "cook_minutes")}),
        ("Ownership / Timestamps", {"fields": ("created_by", "created_at", "updated_at")}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ("name", "default_recipe", "is_active", "created_by", "updated_at", "cook_session_count")
    list_filter = ("is_active",)
    search_fields = ("name", "description", "default_recipe__title")
    readonly_fields = ("created_at", "updated_at")
    inlines = (ReferenceURLInline, PDFDocumentInline, NoteInline, TrackedImageInline)
    autocomplete_fields = ("default_recipe",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_cook_session_count=Count("cook_sessions"))

    def cook_session_count(self, obj: Dish):
        return getattr(obj, "_cook_session_count", 0)

    cook_session_count.short_description = "Cook sessions"

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CookSession)
class CookSessionAdmin(admin.ModelAdmin):
    list_display = ("cooked_on", "dish", "meal_type", "method", "duration_minutes", "created_by", "has_result")
    list_filter = ("meal_type", "method", "cooked_on")
    search_fields = ("dish__name", "recipe_used__title", "summary")
    date_hierarchy = "cooked_on"
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("dish", "recipe_used")
    inlines = (NoteInline, TrackedImageInline, ReferenceURLInline, PDFDocumentInline)
    fieldsets = (
        (None, {"fields": ("dish", "recipe_used", "cooked_on")}),
        ("Details", {"fields": ("meal_type", "method", "servings_made", "duration_minutes", "summary", "is_active")}),
        ("Ownership / Timestamps", {"fields": ("created_by", "created_at", "updated_at")}),
    )

    def has_result(self, obj: CookSession):
        return hasattr(obj, "result")

    has_result.boolean = True
    has_result.short_description = "Result?"

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CookResult)
class CookResultAdmin(admin.ModelAdmin):
    list_display = ("cook_session", "outcome", "overall_rating", "would_make_again", "updated_at", "created_by")
    list_filter = ("outcome", "would_make_again")
    search_fields = ("cook_session__dish__name", "what_worked", "what_to_change", "next_time_plan")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("cook_session",)
    inlines = (NoteInline, TrackedImageInline, ReferenceURLInline, PDFDocumentInline)

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "content_type", "object_id", "is_pinned", "updated_at", "created_by")
    list_filter = ("is_pinned", "content_type")
    search_fields = ("title", "body", "object_id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(TrackedImage)
class TrackedImageAdmin(admin.ModelAdmin):
    list_display = ("uuid", "content_type", "object_id", "is_cover", "sort_order", "created_at", "created_by")
    list_filter = ("is_cover", "content_type")
    search_fields = ("uuid", "caption", "alt_text", "object_id")
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(ReferenceURL)
class ReferenceURLAdmin(admin.ModelAdmin):
    list_display = ("kind", "title", "url", "is_primary", "content_type", "object_id", "created_at", "created_by")
    list_filter = ("kind", "is_primary", "content_type")
    search_fields = ("title", "url", "description", "object_id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PDFDocument)
class PDFDocumentAdmin(admin.ModelAdmin):
    list_display = ("kind", "title", "original_filename", "content_type", "object_id", "created_at", "created_by")
    list_filter = ("kind", "content_type")
    search_fields = ("title", "original_filename", "description", "object_id")
    readonly_fields = ("uuid", "created_at", "updated_at", "original_filename")
