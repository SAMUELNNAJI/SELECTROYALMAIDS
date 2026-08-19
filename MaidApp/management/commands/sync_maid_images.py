from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from MaidApp.models import MaidProfile


class Command(BaseCommand):
    help = "Attach image files to maid profiles by matching their legacy photo filenames."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default="media/maids",
            help="Folder containing the downloaded legacy maid images.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Replace a profile image that is already uploaded.",
        )

    def handle(self, *args, **options):
        source = Path(options["source"])
        if not source.is_dir():
            raise CommandError(f"Image folder does not exist: {source}")

        images = {
            image.name.casefold(): image
            for image in source.iterdir()
            if image.is_file() and image.suffix.casefold() in {".jpg", ".jpeg", ".png", ".webp"}
        }
        if not images:
            raise CommandError(f"No supported images found in: {source}")

        matched_names = set()
        imported = skipped = 0

        for profile in MaidProfile.objects.exclude(photo_filename=""):
            filename = Path(profile.photo_filename).name
            image_path = images.get(filename.casefold())
            if image_path is None:
                continue

            matched_names.add(image_path.name.casefold())
            if profile.image and not options["replace"]:
                skipped += 1
                continue

            with image_path.open("rb") as image_file:
                profile.image.save(image_path.name, File(image_file), save=True)
            imported += 1
            self.stdout.write(f"Attached: {profile.full_name} <- {image_path.name}")

        unmatched = len(images) - len(matched_names)
        self.stdout.write(self.style.SUCCESS(
            f"Done. Attached {imported}; already present {skipped}; image files without a SQL match {unmatched}."
        ))
