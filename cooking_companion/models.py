# cooking_companion/models.py
from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


# ----------------------------
# Reusable base mixins
# ----------------------------

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class OwnedModel(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_created",
        null=True,
        blank=True,
        db_index=True,
    )

    class Meta:
        abstract = True


# ----------------------------
# Core domain
# ----------------------------

class Recipe(TimeStampedModel, OwnedModel):
    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)

    author = models.CharField(max_length=200, blank=True)

    ingredients = models.TextField(blank=True)
    instructions = models.TextField(blank=True)

    yield_text = models.CharField(max_length=100, blank=True)  # e.g. "Makes 12 cookies"
    prep_minutes = models.PositiveIntegerField(null=True, blank=True)
    cook_minutes = models.PositiveIntegerField(null=True, blank=True)

    is_favorite = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-updated_at", "title"]
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["is_favorite", "updated_at"]),
        ]

    def __str__(self) -> str:
        return self.title


class Dish(TimeStampedModel, OwnedModel):
    """
    A conceptual "thing you cook" (e.g., 'Oven Bacon', 'Hoppin John', 'Pan Eggs').
    Cook sessions record each time you make it.
    """
    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)

    default_recipe = models.ForeignKey(
        Recipe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_dishes",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["created_by", "name"],
                name="uniq_dish_per_owner_name",
            )
        ]

    def __str__(self) -> str:
        return self.name


class CookSession(TimeStampedModel, OwnedModel):
    """
    A single cooking event / log entry.
    """
    class MealType(models.TextChoices):
        BREAKFAST = "breakfast", "Breakfast"
        LUNCH = "lunch", "Lunch"
        DINNER = "dinner", "Dinner"
        SNACK = "snack", "Snack"
        DESSERT = "dessert", "Dessert"
        OTHER = "other", "Other"

    class CookMethod(models.TextChoices):
        STOVETOP = "stovetop", "Stovetop"
        OVEN = "oven", "Oven"
        GRILL = "grill", "Grill"
        AIR_FRYER = "air_fryer", "Air fryer"
        MICROWAVE = "microwave", "Microwave"
        NO_COOK = "no_cook", "No-cook"
        OTHER = "other", "Other"

    dish = models.ForeignKey(Dish, on_delete=models.PROTECT, related_name="cook_sessions")
    recipe_used = models.ForeignKey(
        Recipe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cook_sessions",
    )

    cooked_on = models.DateField(default=timezone.localdate, db_index=True)
    meal_type = models.CharField(max_length=20, choices=MealType.choices, default=MealType.OTHER)
    method = models.CharField(max_length=20, choices=CookMethod.choices, default=CookMethod.OTHER)

    servings_made = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)

    summary = models.CharField(max_length=280, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-cooked_on", "-created_at"]
        indexes = [
            models.Index(fields=["cooked_on", "dish"]),
            models.Index(fields=["created_by", "cooked_on"]),
            models.Index(fields=["meal_type", "cooked_on"]),
        ]

    def __str__(self) -> str:
        return f"{self.dish} @ {self.cooked_on}"


class CookResult(TimeStampedModel, OwnedModel):
    """
    Outcome/assessment for a CookSession.
    """
    class Outcome(models.TextChoices):
        NAILED_IT = "nailed_it", "Nailed it"
        GOOD = "good", "Good"
        OKAY = "okay", "Okay"
        FAIL = "fail", "Fail"
        EXPERIMENT = "experiment", "Experiment / Unknown"

    cook_session = models.OneToOneField(
        CookSession,
        on_delete=models.CASCADE,
        related_name="result",
    )

    outcome = models.CharField(max_length=20, choices=Outcome.choices, default=Outcome.EXPERIMENT)

    overall_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="1–10",
    )
    taste_rating = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    texture_rating = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    appearance_rating = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(10)]
    )

    would_make_again = models.BooleanField(default=False)

    what_worked = models.TextField(blank=True)
    what_to_change = models.TextField(blank=True)
    next_time_plan = models.TextField(blank=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["outcome"]),
            models.Index(fields=["would_make_again", "outcome"]),
        ]

    def __str__(self) -> str:
        return f"Result for {self.cook_session}"


# ----------------------------
# Generic Notes + Images + URLs + PDF docs (attachable to any model)
# ----------------------------

class Note(TimeStampedModel, OwnedModel):
    """
    Generic note attachable to any model (Dish, Recipe, CookSession, CookResult, etc.).
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64, db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")

    title = models.CharField(max_length=200, blank=True)
    body = models.TextField()

    is_pinned = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_pinned", "-updated_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["created_by", "updated_at"]),
        ]

    def __str__(self) -> str:
        return self.title or f"Note {self.pk}"


def cooking_companion_image_upload_to(instance: "TrackedImage", filename: str) -> str:
    # repo/app name + stable uuid path
    return f"cooking-companion/images/{instance.uuid}/{filename}"


class TrackedImage(TimeStampedModel, OwnedModel):
    """
    Generic image attachable to any model (Dish, Recipe, CookSession, CookResult, etc.).
    Supports multiple images per target + ordering + cover flag.
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64, db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")

    image = models.ImageField(upload_to=cooking_companion_image_upload_to)
    caption = models.CharField(max_length=300, blank=True)
    alt_text = models.CharField(max_length=300, blank=True)

    taken_at = models.DateTimeField(null=True, blank=True)

    sort_order = models.PositiveIntegerField(default=0)
    is_cover = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["created_by", "created_at"]),
            models.Index(fields=["is_cover", "sort_order"]),
        ]

    def __str__(self) -> str:
        return f"Image {self.uuid}"


class ReferenceURL(TimeStampedModel, OwnedModel):
    """
    Generic URL attachable to any model. Use for:
    - original recipe page
    - YouTube video
    - product page (pan, thermometer)
    - ingredient reference
    - anything “I want to remember this link”
    """
    class Kind(models.TextChoices):
        RECIPE = "recipe", "Recipe"
        VIDEO = "video", "Video"
        PRODUCT = "product", "Product"
        ARTICLE = "article", "Article"
        OTHER = "other", "Other"

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64, db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")

    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OTHER)

    title = models.CharField(max_length=200, blank=True)
    url = models.URLField()
    description = models.TextField(blank=True)

    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["kind"]),
            models.Index(fields=["created_by", "created_at"]),
            models.Index(fields=["is_primary", "sort_order"]),
        ]

    def __str__(self) -> str:
        return self.title or self.url


def cooking_companion_pdf_upload_to(instance: "PDFDocument", filename: str) -> str:
    return f"cooking-companion/pdfs/{instance.uuid}/{filename}"


class PDFDocument(TimeStampedModel, OwnedModel):
    """
    Generic PDF upload attachable to any model.
    Use for:
    - PDF recipes
    - scanned recipe cards
    - cooking notes exported as PDF
    - any supporting cooking document
    """
    class Kind(models.TextChoices):
        RECIPE = "recipe", "Recipe"
        REFERENCE = "reference", "Reference"
        INSTRUCTIONS = "instructions", "Instructions"
        OTHER = "other", "Other"

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64, db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")

    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OTHER)

    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    pdf = models.FileField(upload_to=cooking_companion_pdf_upload_to)
    original_filename = models.CharField(max_length=255, blank=True)

    page_count = models.PositiveIntegerField(null=True, blank=True)  # optional: compute later
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["kind"]),
            models.Index(fields=["created_by", "created_at"]),
        ]

    def __str__(self) -> str:
        return self.title or (self.original_filename or f"PDF {self.uuid}")

    def save(self, *args, **kwargs):
        # Convenience: keep original filename if not provided
        if self.pdf and not self.original_filename:
            self.original_filename = self.pdf.name.split("/")[-1]
        super().save(*args, **kwargs)
