from django.db import migrations

SERVICES = [
    {
        "slug": "maid",
        "title": "Maid / House Help",
        "badge_label": "Most Popular",
        "badge_color": "blue",
        "icon": "fa-broom",
        "description": (
            "Our most requested service. Whether you need a live-in or live-out "
            "housekeeper, our verified maids handle all aspects of domestic management "
            "— from deep cleaning and laundry to cooking and childcare support."
        ),
        "features": (
            "Daily cleaning & deep cleaning\n"
            "Laundry, ironing & wardrobe management\n"
            "Cooking & meal preparation\n"
            "Childcare support\n"
            "Grocery shopping & errands\n"
            "Live-in or live-out arrangements"
        ),
        "image_url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&q=80",
        "available_count": "820+",
        "avg_rating": "4.9★",
        "guarantee_days": 30,
        "order": 1,
    },
    {
        "slug": "cook",
        "title": "Cook / Chef",
        "badge_label": "In Demand",
        "badge_color": "orange",
        "icon": "fa-utensils",
        "description": (
            "Hire an experienced cook who understands Nigerian cuisine and beyond. "
            "Our chefs are skilled in local delicacies, continental dishes, and "
            "dietary-specific meals — perfect for busy families and executives."
        ),
        "features": (
            "Nigerian & continental cuisine\n"
            "Daily meal planning & preparation\n"
            "Dietary & health-conscious cooking\n"
            "Event & party catering\n"
            "Kitchen management & hygiene\n"
            "Grocery sourcing & budget management"
        ),
        "image_url": "https://images.unsplash.com/photo-1507048331197-7d4ac70811cf?w=600&q=80",
        "available_count": "310+",
        "avg_rating": "4.8★",
        "guarantee_days": 21,
        "order": 2,
    },
    {
        "slug": "nanny",
        "title": "Baby Sitter",
        "badge_label": "Highly Rated",
        "badge_color": "green",
        "icon": "fa-baby",
        "description": (
            "Caring, trained babysitters who keep your children safe, engaged and happy. "
            "From toddlers to school-age children, our babysitters are vetted for patience, "
            "reliability and genuine love for childcare."
        ),
        "features": (
            "Safe supervision & child engagement\n"
            "Age-appropriate play & activities\n"
            "Homework support\n"
            "Feeding, bathing & bedtime routines\n"
            "Emergency first-aid trained\n"
            "Flexible hours including evenings"
        ),
        "image_url": "https://images.unsplash.com/photo-1555252333-9f8e92e65df9?w=600&q=80",
        "available_count": "430+",
        "avg_rating": "4.9★",
        "guarantee_days": 21,
        "order": 3,
    },
    {
        "slug": "elderly",
        "title": "Elderly Care",
        "badge_label": "Compassionate",
        "badge_color": "purple",
        "icon": "fa-heart-pulse",
        "description": (
            "Our elderly caregivers are selected for their compassion, patience, and dedication. "
            "They provide dignified, professional support for your loved ones — enabling them "
            "to live comfortably at home with assistance."
        ),
        "features": (
            "Daily living assistance & mobility support\n"
            "Medication reminders & health monitoring\n"
            "Personal hygiene & grooming\n"
            "Companionship & emotional support\n"
            "Light housekeeping & meal preparation\n"
            "Medical appointment accompaniment"
        ),
        "image_url": "https://images.unsplash.com/photo-1576765608535-5f04d1e3f289?w=600&q=80",
        "available_count": "240+",
        "avg_rating": "4.9★",
        "guarantee_days": 30,
        "order": 4,
    },
]


def seed_services(apps, schema_editor):
    Service = apps.get_model("MaidApp", "Service")
    for data in SERVICES:
        Service.objects.get_or_create(slug=data["slug"], defaults=data)


def unseed_services(apps, schema_editor):
    Service = apps.get_model("MaidApp", "Service")
    for data in SERVICES:
        Service.objects.filter(slug=data["slug"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("MaidApp", "0005_service_model"),
    ]

    operations = [
        migrations.RunPython(seed_services, reverse_code=unseed_services),
    ]
