from django.core.management.base import BaseCommand
from core.models import Admin

class Command(BaseCommand):
    help = 'Seeds initial custom admin user for testing and development'

    def handle(self, *args, **options):
        username = 'admin_gunungmas'
        email = 'admin@gunungmas.com'
        password = 'password123'

        # Cari atau buat record admin kustom
        admin, created = Admin.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'password': password
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Sukses: Akun admin '{username}' berhasil dibuat!"))
        else:
            self.stdout.write(self.style.WARNING(f"Info: Akun admin '{username}' sudah ada di database."))
