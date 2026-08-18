from django.db import migrations

FAQS = [
    (
        1,
        "How long does the hiring process take?",
        "Most employers find a suitable candidate within 5–7 business days. "
        "After shortlisting and interviews, the full placement can be completed "
        "within 1–2 weeks depending on your requirements and availability.",
    ),
    (
        2,
        "Are all candidates background-checked?",
        "Yes. Every candidate on our platform undergoes a 7-point verification "
        "process including NIN verification, criminal background checks, reference "
        "checks from previous employers, and a skills assessment before their "
        "profile is listed.",
    ),
    (
        3,
        "What if I'm not satisfied with my hire?",
        "We offer a free replacement guarantee within the agreed guarantee period. "
        "Simply contact our support team and we will immediately begin sourcing a "
        "suitable replacement at no additional cost to you.",
    ),
    (
        4,
        "Can I interview candidates before hiring?",
        "Absolutely. You can schedule video or in-person interviews directly through "
        "our platform at a time that suits you. We encourage interviewing multiple "
        "candidates before making your final decision.",
    ),
]


def seed_faqs(apps, schema_editor):
    FAQ = apps.get_model("MaidApp", "FAQ")
    for order, question, answer in FAQS:
        FAQ.objects.get_or_create(
            question=question,
            defaults={"answer": answer, "order": order, "is_active": True},
        )


def unseed_faqs(apps, schema_editor):
    FAQ = apps.get_model("MaidApp", "FAQ")
    for _, question, _ in FAQS:
        FAQ.objects.filter(question=question).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("MaidApp", "0003_faq_model"),
    ]

    operations = [
        migrations.RunPython(seed_faqs, reverse_code=unseed_faqs),
    ]
