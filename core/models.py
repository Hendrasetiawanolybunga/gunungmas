from django.db import models

class Admin(models.Model):
    id_admin = models.AutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255)  # Akan disimpan dalam bentuk hash/plain sesuai kebutuhan logic login manual
    email = models.EmailField(max_length=100, unique=True)

    def __str__(self):
        return self.username

class Bus(models.Model):
    id_bus = models.AutoField(primary_key=True)
    nama_bus = models.CharField(max_length=50) # Contoh: Gunung Mas 01
    nomor_polisi = models.CharField(max_length=15)
    kapasitas = models.IntegerField() # Lux: 8, Premium: 8, Std: 10
    tipe_bus = models.CharField(max_length=20) # Lux, Premium, Std
    foto = models.ImageField(upload_to='bus_photos/', blank=True, null=True)
    sopir = models.OneToOneField('Sopir', on_delete=models.SET_NULL, null=True, blank=True, db_column='id_sopir')

    def __str__(self):
        return f"{self.nama_bus} ({self.tipe_bus})"

class Rute(models.Model):
    id_rute = models.AutoField(primary_key=True)
    kota_asal = models.CharField(max_length=50)
    kota_tujuan = models.CharField(max_length=50)
    jarak = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.kota_asal} - {self.kota_tujuan}"

class Sopir(models.Model):
    id_sopir = models.AutoField(primary_key=True)
    nama_sopir = models.CharField(max_length=100)
    nomor_lisensi = models.CharField(max_length=30) # No SIM
    nomor_telepon = models.CharField(max_length=15)
    status_tugas = models.CharField(max_length=20, default='Tersedia') # Tersedia, Bertugas

    def __str__(self):
        return self.nama_sopir

class Jadwal(models.Model):
    id_jadwal = models.AutoField(primary_key=True)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, db_column='id_bus')
    rute = models.ForeignKey(Rute, on_delete=models.CASCADE, db_column='id_rute')
    tanggal_berangkat = models.DateField()
    jam_berangkat = models.TimeField()
    jam_tiba = models.TimeField()

    def __str__(self):
        return f"{self.rute} | {self.tanggal_berangkat} ({self.jam_berangkat})"

class Tiket(models.Model):
    id_tiket = models.AutoField(primary_key=True)
    jadwal = models.ForeignKey(Jadwal, on_delete=models.CASCADE, db_column='id_jadwal')
    harga_tiket = models.DecimalField(max_digits=10, decimal_places=0) # Contoh: 180000
    status = models.CharField(max_length=20, default='Tersedia') # Tersedia, Habis

    def __str__(self):
        return f"Tiket #{self.id_tiket} - {self.jadwal.rute} (Rp {self.harga_tiket})"

class Pelanggan(models.Model):
    id_pelanggan = models.AutoField(primary_key=True)
    nama_pelanggan = models.CharField(max_length=100)
    jenis_kelamin = models.CharField(max_length=15)
    alamat = models.TextField()
    nomor_telpon = models.CharField(max_length=15)
    email = models.EmailField(max_length=100, unique=True, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.nama_pelanggan

class Pemesanan(models.Model):
    id_pemesanan = models.AutoField(primary_key=True)
    pelanggan = models.ForeignKey(Pelanggan, on_delete=models.CASCADE, db_column='id_pelanggan')
    tiket = models.ForeignKey(Tiket, on_delete=models.CASCADE, db_column='id_tiket')
    tanggal_pesan = models.DateField(auto_now_add=True)
    jumlah_tiket = models.IntegerField(default=1)
    bagasi = models.IntegerField(default=0) # Berat dalam Kg atau status bagasi
    nomor_kursi = models.CharField(max_length=50, blank=True, null=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    def __str__(self):
        return f"Pemesanan #{self.id_pemesanan} oleh {self.pelanggan.nama_pelanggan}"

class Pembayaran(models.Model):
    id_pembayaran = models.AutoField(primary_key=True)
    pelanggan = models.ForeignKey(Pelanggan, on_delete=models.CASCADE, db_column='id_pelanggan')
    metode_bayar = models.CharField(max_length=20, default='Online', blank=True, null=True)
    jumlah_bayar = models.DecimalField(max_digits=10, decimal_places=0)
    status = models.CharField(max_length=20, default='Belum Lunas') # Lunas, Belum Lunas
    order_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    snap_token = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Pembayaran #{self.id_pembayaran} - {self.status}"
