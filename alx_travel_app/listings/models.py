# from django.db import models
#
# Create your models here.
#
# #!/usr/bin/env python3
"""
Listings models: Listing, Booking, Review
"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Listing(models.Model):
    """A property/listing that can be booked by users."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listings",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    price_per_night = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[
            MinValueValidator(
                Decimal("0.00"))])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} — {self.location}"


class Booking(models.Model):
    """A booking for a Listing made by a user (guest)."""
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELED, "Canceled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="bookings"
    )
    guest = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[
            MinValueValidator(
                Decimal("0.00"))])
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Booking {self.id} for {self.listing.title}"

    def clean(self) -> None:
        """Optionally validate that end_date is after start_date."""
        from django.core.exceptions import ValidationError

        if self.end_date < self.start_date:
            raise ValidationError("end_date must be after start_date")

    def save(self, *args, **kwargs) -> None:
        """
        Optionally compute total_price if not set (assuming price_per_night available).
        This simple computation will override only when total_price is None or 0.
        """
        if not self.total_price or self.total_price == Decimal("0.00"):
            nights = (self.end_date - self.start_date).days
            if nights > 0:
                self.total_price = self.listing.price_per_night * nights
        super().save(*args, **kwargs)


class Review(models.Model):
    """A review (rating + comment) left by a user about a Listing."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews")
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Review {self.rating} by {self.user} on {self.listing.title}"
