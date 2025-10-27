#!/usr/bin/env python3
"""
Serializers for the listings app: ListingSerializer, BookingSerializer.
"""
from rest_framework import serializers
from .models import Listing, Booking


class ListingSerializer(serializers.ModelSerializer):
    """Serializer for Listing model."""

    host = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Listing
        fields = [
            "id",
            "host",
            "title",
            "description",
            "location",
            "price_per_night",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "host", "created_at", "updated_at"]


class BookingSerializer(serializers.ModelSerializer):
    """Serializer for Booking model."""

    listing = serializers.PrimaryKeyRelatedField(
        queryset=Listing.objects.all())
    guest = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "listing",
            "guest",
            "start_date",
            "end_date",
            "total_price",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "guest", "created_at"]
