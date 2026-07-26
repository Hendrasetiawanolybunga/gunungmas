from django.core.management.base import BaseCommand
from core.models import Bus, Rute, Jadwal, Tiket, Pelanggan, Pemesanan, Pembayaran
import datetime

class Command(BaseCommand):
    help = 'Seeds initial dummy data based on Gunung Mas interview results'

    def handle(self, *args, **options):
        self.stdout.write("Memulai proses seeding data dummy...")

        # 1. Seeding Data Bus
        b1, _ = Bus.objects.get_or_create(nama_bus="Gunung Mas 01", nomor_polisi="EB 1234 GA", defaults={'kapasitas': 8, 'tipe_bus': 'Lux'})
        b2, _ = Bus.objects.get_or_create(nama_bus="Gunung Mas 02", nomor_polisi="EB 5678 GA", defaults={'kapasitas': 8, 'tipe_bus': 'Premium'})
        b3, _ = Bus.objects.get_or_create(nama_bus="Gunung Mas 03", nomor_polisi="EB 9012 GA", defaults={'kapasitas': 10, 'tipe_bus': 'Std'})
        self.stdout.write(self.style.SUCCESS("- Data Bus berhasil disinkronisasi."))

        # 2. Seeding Data Rute
        r1, _ = Rute.objects.get_or_create(kota_asal="Labuan Bajo", kota_tujuan="Ruteng", defaults={'jarak': '130 km'})
        r2, _ = Rute.objects.get_or_create(kota_asal="Ruteng", kota_tujuan="Bajawa", defaults={'jarak': '135 km'})
        r3, _ = Rute.objects.get_or_create(kota_asal="Ruteng", kota_tujuan="Ende", defaults={'jarak': '260 km'})
        r4, _ = Rute.objects.get_or_create(kota_asal="Ruteng", kota_tujuan="Maumere", defaults={'jarak': '340 km'})
        self.stdout.write(self.style.SUCCESS("- Data Rute berhasil disinkronisasi."))

        # 3. Seeding Data Jadwal & Tiket Otomatis
        # Jadwal 1: LB - RTG (Premium) jam 07:00 pagi besok
        besok = datetime.date.today() + datetime.timedelta(days=1)
        j1, _ = Jadwal.objects.get_or_create(
            bus=b2, rute=r1, tanggal_berangkat=besok,
            jam_berangkat=datetime.time(7, 0), jam_tiba=datetime.time(11, 0)
        )
        t1, _ = Tiket.objects.get_or_create(jadwal=j1, defaults={'harga_tiket': 180000, 'status': 'Tersedia'})

        # Jadwal 2: RTG - MME (Lux) jam 08:00 pagi besok
        j2, _ = Jadwal.objects.get_or_create(
            bus=b1, rute=r4, tanggal_berangkat=besok,
            jam_berangkat=datetime.time(8, 0), jam_tiba=datetime.time(17, 0)
        )
        t2, _ = Tiket.objects.get_or_create(jadwal=j2, defaults={'harga_tiket': 200000, 'status': 'Tersedia'})
        self.stdout.write(self.style.SUCCESS("- Data Jadwal dan Tiket berhasil disinkronisasi."))

        # 4. Seeding Data Pelanggan, Pemesanan, Pembayaran (Uji Transaksi)
        p1, p1_created = Pelanggan.objects.get_or_create(
            email="mario@gmail.com",
            defaults={
                'nama_pelanggan': 'Mario Nagung',
                'jenis_kelamin': 'Laki-laki',
                'alamat': 'Ruteng, Flores',
                'nomor_telpon': '081234567890',
                'password': 'penumpang123'
            }
        )

        if p1_created:
            # Buat transaksi pemesanan contoh untuk Mario
            pemesanan = Pemesanan.objects.create(pelanggan=p1, tiket=t1, jumlah_tiket=1)
            Pembayaran.objects.create(pelanggan=p1, metode_bayar='Transfer', jumlah_bayar=180000, status='Belum Lunas')
            self.stdout.write(self.style.SUCCESS("- Data Transaksi Dummy (Pelanggan, Pesanan, Bayar) berhasil dibuat."))
        else:
            self.stdout.write(self.style.WARNING("- Data Transaksi Dummy sudah ada."))

        self.stdout.write(self.style.SUCCESS("Selesai: Seluruh data dummy berhasil dimasukkan!"))
