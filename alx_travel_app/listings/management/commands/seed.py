#!/usr/bin/env python3
"""
Django management command to seed the database with sample Listing data.

Usage:
    python manage.py seed
"""
from typing import List, Dict
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from listings.models import Listing
from django.db import transaction


SAMPLE_LISTINGS: List[Dict] = [
    {
        "title": "Cozy Downtown Flat",
        "description": "A comfortable one-bedroom flat in the heart of the city.",
        "location": "Lagos, Nigeria",
        "price_per_night": "40.00",
    },
    {
        "title": "Beachside Bungalow",
        "description": "Relax by the sea with private beach access.",
        "location": "Accra, Ghana",
        "price_per_night": "75.00",
    },
    {
        "title": "Mountain Cabin Retreat",
        "description": "Quiet cabin with great hiking nearby.",
        "location": "Kano, Nigeria",
        "price_per_night": "55.00",
    },
]


class Command(BaseCommand):
    """Seed the database with sample listings."""

    help = "Seed the database with sample listings for development"

    def handle(self, *args, **options) -> None:  # noqa: D401 - documentation
        User = get_user_model()
        host_username = "sample-host"

        # Create or reuse a host user
        host, created = User.objects.get_or_create(
            username=host_username,
            defaults={"email": "host@example.com"}
        )
        if created:
            # If the model supports set_password, create a usable password
            try:
                host.set_password("password123")
                host.save()
                self.stdout.write(self.style.SUCCESS(f"Created host user '{host_username}'"))
            except Exception:
                # Some custom user models create users differently
                host.save()
                self.stdout.write(self.style.SUCCESS(f"Created host user '{host_username}' (no password set)"))
        else:
            self.stdout.write(self.style.NOTICE(f"Using existing host user '{host_username}'"))

        # Create listings inside a transaction
        created_count = 0
        with transaction.atomic():
            for item in SAMPLE_LISTINGS:
                listing, _ = Listing.objects.get_or_create(
                    host=host,
                    title=item["title"],
                    defaults={
                        "description": item["description"],
                        "location": item["location"],
                        "price_per_night": item["price_per_night"],
                    },
                )
                # if created now increment
                if listing:
                    created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded listings (ensured sample data present)."))

