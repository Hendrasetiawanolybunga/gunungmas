from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from .models import Admin, Bus, Rute, Sopir, Jadwal, Tiket, Pelanggan, Pemesanan, Pembayaran
import os
from django.conf import settings
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json
import time
import midtransclient
import qrcode
from cryptography.fernet import Fernet
from django.core.files import File
from django.http import JsonResponse


def login_view(request):
    # Jika admin sudah login tapi iseng buka halaman login lagi, oper ke dashboard
    if 'admin_id' in request.session:
        return redirect('dashboard')
        
    if request.method == 'POST':
        user_input = request.POST.get('username')
        pass_input = request.POST.get('password')
        
        try:
            # Query manual ke tabel Admin kustom
            admin = Admin.objects.get(username=user_input, password=pass_input)
            
            # Set Session Kustom
            request.session['admin_id'] = admin.id_admin
            request.session['admin_username'] = admin.username
            
            messages.success(request, f"Selamat datang kembali, {admin.username}!")
            return redirect('dashboard')
            
        except Admin.DoesNotExist:
            messages.error(request, "Username atau password salah!")
            return render(request, 'core/login.html')
            
    return render(request, 'core/login.html')

def logout_view(request):
    request.session.flush() # Hapus semua session data
    messages.success(request, "Anda telah berhasil keluar sistem.")
    return redirect('login')

def dashboard_view(request):
    # Proteksi Halaman Dashboard
    if 'admin_id' not in request.session:
        messages.error(request, "Silakan login terlebih dahulu!")
        return redirect('login')
        
    import datetime
    total_bus = Bus.objects.count()
    total_rute = Rute.objects.count()
    total_jadwal = Jadwal.objects.count()
    total_pemesanan_hari_ini = Pemesanan.objects.filter(tanggal_pesan=datetime.date.today()).count()
    
    pemesanan_terbaru = Pemesanan.objects.all().select_related('pelanggan', 'tiket__jadwal__rute', 'tiket__jadwal__bus').order_by('-id_pemesanan')[:5]
        
    context = {
        'username': request.session.get('admin_username'),
        'total_bus': total_bus,
        'total_rute': total_rute,
        'total_jadwal': total_jadwal,
        'total_pemesanan_hari_ini': total_pemesanan_hari_ini,
        'pemesanan_terbaru': pemesanan_terbaru,
    }
    return render(request, 'core/dashboard.html', context)

def bus_index(request):
    if 'admin_id' not in request.session:
        return redirect('login')
    
    # Ambil semua data bus dari database
    semua_bus = Bus.objects.all().order_by('-id_bus')
    context = {
        'username': request.session.get('admin_username'),
        'semua_bus': semua_bus
    }
    return render(request, 'core/bus/index.html', context)

def bus_add(request):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    if request.method == 'POST':
        nama_bus = request.POST.get('nama_bus')
        nomor_polisi = request.POST.get('nomor_polisi')
        tipe_bus = request.POST.get('tipe_bus')
        foto = request.FILES.get('foto')
        id_sopir = request.POST.get('id_sopir')
        
        # Logika otomatis kapasitas berdasarkan wawancara (Lux: 8, Premium: 8, Std: 10)
        kapasitas = 10
        if tipe_bus == 'Lux' or tipe_bus == 'Premium':
            kapasitas = 8
            
        sopir_obj = None
        if id_sopir:
            # Validasi: Cek apakah sopir sudah punya bus
            if Bus.objects.filter(sopir_id=id_sopir).exists():
                messages.error(request, "Gagal! Sopir tersebut sudah ditugaskan ke armada bus lain.")
                return redirect('bus_add')
            
            sopir_obj = Sopir.objects.get(pk=id_sopir)
            
        # Simpan ke database
        Bus.objects.create(
            nama_bus=nama_bus,
            nomor_polisi=nomor_polisi,
            kapasitas=kapasitas,
            tipe_bus=tipe_bus,
            foto=foto,
            sopir=sopir_obj
        )
        messages.success(request, f"Bus {nama_bus} berhasil ditambahkan!")
        return redirect('bus_index')
        
    sopir_tersedia = Sopir.objects.filter(bus__isnull=True)
    context = {
        'username': request.session.get('admin_username'),
        'sopir_tersedia': sopir_tersedia
    }
    return render(request, 'core/bus/add.html', context)

def bus_edit(request, id_bus):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    try:
        bus = Bus.objects.get(pk=id_bus)
    except Bus.DoesNotExist:
        messages.error(request, "Data bus tidak ditemukan.")
        return redirect('bus_index')
        
    if request.method == 'POST':
        bus.nama_bus = request.POST.get('nama_bus')
        bus.nomor_polisi = request.POST.get('nomor_polisi')
        bus.tipe_bus = request.POST.get('tipe_bus')
        id_sopir = request.POST.get('id_sopir')
        
        # Update kapasitas otomatis sesuai tipe baru
        if bus.tipe_bus in ['Lux', 'Premium']:
            bus.kapasitas = 8
        else:
            bus.kapasitas = 10
            
        foto = request.FILES.get('foto')
        if foto:
            bus.foto = foto
            
        if id_sopir:
            # Validasi: Cek apakah sopir sudah punya bus SELAIN bus ini
            if Bus.objects.filter(sopir_id=id_sopir).exclude(id_bus=id_bus).exists():
                messages.error(request, "Gagal! Sopir tersebut sudah memegang armada bus lain.")
                return redirect('bus_edit', id_bus=id_bus)
            
            bus.sopir = Sopir.objects.get(pk=id_sopir)
        else:
            bus.sopir = None
            
        bus.save()
        messages.success(request, f"Data bus {bus.nama_bus} berhasil diperbarui!")
        return redirect('bus_index')
        
    semua_sopir = Sopir.objects.all()
    context = {
        'username': request.session.get('admin_username'),
        'bus': bus,
        'semua_sopir': semua_sopir
    }
    return render(request, 'core/bus/edit.html', context)

def bus_delete(request, id_bus):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    if request.method == 'POST':
        try:
            bus = Bus.objects.get(pk=id_bus)
            nama_bus = bus.nama_bus
            bus.delete()
            messages.success(request, f"Bus {nama_bus} berhasil dihapus!")
        except Bus.DoesNotExist:
            messages.error(request, "Data bus gagal dihapus karena tidak ditemukan.")
            
    return redirect('bus_index')

def rute_index(request):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    semua_rute = Rute.objects.all().order_by('-id_rute')
    context = {
        'username': request.session.get('admin_username'),
        'semua_rute': semua_rute
    }
    return render(request, 'core/rute/index.html', context)

def rute_add(request):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    if request.method == 'POST':
        kota_asal = request.POST.get('kota_asal')
        kota_tujuan = request.POST.get('kota_tujuan')
        jarak = request.POST.get('jarak')
        
        Rute.objects.create(
            kota_asal=kota_asal,
            kota_tujuan=kota_tujuan,
            jarak=jarak
        )
        messages.success(request, f"Rute {kota_asal} - {kota_tujuan} berhasil ditambahkan!")
        return redirect('rute_index')
        
    context = {'username': request.session.get('admin_username')}
    return render(request, 'core/rute/add.html', context)

def rute_edit(request, id_rute):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    try:
        rute = Rute.objects.get(pk=id_rute)
    except Rute.DoesNotExist:
        messages.error(request, "Data rute tidak ditemukan.")
        return redirect('rute_index')
        
    if request.method == 'POST':
        rute.kota_asal = request.POST.get('kota_asal')
        rute.kota_tujuan = request.POST.get('kota_tujuan')
        rute.jarak = request.POST.get('jarak')
        rute.save()
        messages.success(request, f"Rute {rute.kota_asal} - {rute.kota_tujuan} berhasil diperbarui!")
        return redirect('rute_index')
        
    context = {
        'username': request.session.get('admin_username'),
        'rute': rute
    }
    return render(request, 'core/rute/edit.html', context)

def rute_delete(request, id_rute):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    if request.method == 'POST':
        try:
            rute = Rute.objects.get(pk=id_rute)
            rute_name = f"{rute.kota_asal} - {rute.kota_tujuan}"
            rute.delete()
            messages.success(request, f"Rute {rute_name} berhasil dihapus!")
        except Rute.DoesNotExist:
            messages.error(request, "Data rute gagal dihapus karena tidak ditemukan.")
            
    return redirect('rute_index')

# Sopir Views
def sopir_index(request):
    if 'admin_id' not in request.session:
        return redirect('login')
    semua_sopir = Sopir.objects.all().order_by('-id_sopir')
    context = {
        'username': request.session.get('admin_username'),
        'semua_sopir': semua_sopir
    }
    return render(request, 'core/sopir/index.html', context)

def sopir_add(request):
    if 'admin_id' not in request.session:
        return redirect('login')
    if request.method == 'POST':
        nama_sopir = request.POST.get('nama_sopir')
        nomor_lisensi = request.POST.get('nomor_lisensi')
        nomor_telepon = request.POST.get('nomor_telepon')
        password = request.POST.get('password')
        status_tugas = request.POST.get('status_tugas', 'Tersedia')
        
        Sopir.objects.create(
            nama_sopir=nama_sopir,
            nomor_lisensi=nomor_lisensi,
            nomor_telepon=nomor_telepon,
            password=password,
            status_tugas=status_tugas
        )
        messages.success(request, f"Sopir {nama_sopir} berhasil ditambahkan!")
        return redirect('sopir_index')
        
    context = {'username': request.session.get('admin_username')}
    return render(request, 'core/sopir/add.html', context)

def sopir_edit(request, id_sopir):
    if 'admin_id' not in request.session:
        return redirect('login')
    try:
        sopir = Sopir.objects.get(pk=id_sopir)
    except Sopir.DoesNotExist:
        messages.error(request, "Data sopir tidak ditemukan.")
        return redirect('sopir_index')
        
    if request.method == 'POST':
        sopir.nama_sopir = request.POST.get('nama_sopir')
        sopir.nomor_lisensi = request.POST.get('nomor_lisensi')
        sopir.nomor_telepon = request.POST.get('nomor_telepon')
        sopir.status_tugas = request.POST.get('status_tugas')
        
        password = request.POST.get('password')
        if password:
            sopir.password = password
            
        sopir.save()
        messages.success(request, f"Data sopir {sopir.nama_sopir} berhasil diperbarui!")
        return redirect('sopir_index')
        
    context = {
        'username': request.session.get('admin_username'),
        'sopir': sopir
    }
    return render(request, 'core/sopir/edit.html', context)

def sopir_delete(request, id_sopir):
    if 'admin_id' not in request.session:
        return redirect('login')
    if request.method == 'POST':
        try:
            sopir = Sopir.objects.get(pk=id_sopir)
            nama_sopir = sopir.nama_sopir
            sopir.delete()
            messages.success(request, f"Sopir {nama_sopir} berhasil dihapus!")
        except Sopir.DoesNotExist:
            messages.error(request, "Data sopir gagal dihapus karena tidak ditemukan.")
    return redirect('sopir_index')

# Jadwal Views
def jadwal_index(request):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    semua_jadwal = Jadwal.objects.all().select_related('bus', 'rute').order_by('-id_jadwal')
    context = {
        'username': request.session.get('admin_username'),
        'semua_jadwal': semua_jadwal
    }
    return render(request, 'core/jadwal/index.html', context)

def jadwal_add(request):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    if request.method == 'POST':
        id_bus = request.POST.get('id_bus')
        id_rute = request.POST.get('id_rute')
        tanggal_berangkat = request.POST.get('tanggal_berangkat')
        jam_berangkat = request.POST.get('jam_berangkat')
        jam_tiba = request.POST.get('jam_tiba')
        
        try:
            bus = Bus.objects.get(pk=id_bus)
            rute = Rute.objects.get(pk=id_rute)
            
            Jadwal.objects.create(
                bus=bus,
                rute=rute,
                tanggal_berangkat=tanggal_berangkat,
                jam_berangkat=jam_berangkat,
                jam_tiba=jam_tiba
            )
            messages.success(request, "Jadwal keberangkatan berhasil ditambahkan!")
            return redirect('jadwal_index')
        except (Bus.DoesNotExist, Rute.DoesNotExist):
            messages.error(request, "Bus atau Rute tidak valid.")
            
    list_bus = Bus.objects.all()
    list_rute = Rute.objects.all()
    context = {
        'username': request.session.get('admin_username'),
        'list_bus': list_bus,
        'list_rute': list_rute
    }
    return render(request, 'core/jadwal/add.html', context)

def jadwal_edit(request, id_jadwal):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    try:
        jadwal = Jadwal.objects.get(pk=id_jadwal)
    except Jadwal.DoesNotExist:
        messages.error(request, "Jadwal tidak ditemukan.")
        return redirect('jadwal_index')
        
    if request.method == 'POST':
        id_bus = request.POST.get('id_bus')
        id_rute = request.POST.get('id_rute')
        jadwal.tanggal_berangkat = request.POST.get('tanggal_berangkat')
        jadwal.jam_berangkat = request.POST.get('jam_berangkat')
        jadwal.jam_tiba = request.POST.get('jam_tiba')
        
        try:
            jadwal.bus = Bus.objects.get(pk=id_bus)
            jadwal.rute = Rute.objects.get(pk=id_rute)
            jadwal.save()
            messages.success(request, "Jadwal keberangkatan berhasil diperbarui!")
            return redirect('jadwal_index')
        except (Bus.DoesNotExist, Rute.DoesNotExist):
            messages.error(request, "Bus atau Rute tidak valid.")
            
    list_bus = Bus.objects.all()
    list_rute = Rute.objects.all()
    context = {
        'username': request.session.get('admin_username'),
        'jadwal': jadwal,
        'list_bus': list_bus,
        'list_rute': list_rute
    }
    return render(request, 'core/jadwal/edit.html', context)

def jadwal_delete(request, id_jadwal):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    if request.method == 'POST':
        try:
            jadwal = Jadwal.objects.get(pk=id_jadwal)
            jadwal.delete()
            messages.success(request, "Jadwal keberangkatan berhasil dihapus!")
        except Jadwal.DoesNotExist:
            messages.error(request, "Jadwal gagal dihapus karena tidak ditemukan.")
            
    return redirect('jadwal_index')

# Tiket Views
def tiket_index(request):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    semua_tiket = Tiket.objects.all().select_related('jadwal__rute', 'jadwal__bus').order_by('-id_tiket')
    context = {
        'username': request.session.get('admin_username'),
        'semua_tiket': semua_tiket
    }
    return render(request, 'core/tiket/index.html', context)

def tiket_add(request):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    if request.method == 'POST':
        id_jadwal = request.POST.get('id_jadwal')
        harga_tiket = request.POST.get('harga_tiket')
        status = request.POST.get('status')
        
        try:
            jadwal = Jadwal.objects.get(pk=id_jadwal)
            Tiket.objects.create(
                jadwal=jadwal,
                harga_tiket=harga_tiket,
                status=status
            )
            messages.success(request, "Tiket baru berhasil diterbitkan!")
            return redirect('tiket_index')
        except Jadwal.DoesNotExist:
            messages.error(request, "Jadwal tidak valid.")
            
    list_jadwal = Jadwal.objects.all().select_related('bus', 'rute')
    context = {
        'username': request.session.get('admin_username'),
        'list_jadwal': list_jadwal
    }
    return render(request, 'core/tiket/add.html', context)

def tiket_edit(request, id_tiket):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    try:
        tiket = Tiket.objects.get(pk=id_tiket)
    except Tiket.DoesNotExist:
        messages.error(request, "Tiket tidak ditemukan.")
        return redirect('tiket_index')
        
    if request.method == 'POST':
        id_jadwal = request.POST.get('id_jadwal')
        tiket.harga_tiket = request.POST.get('harga_tiket')
        tiket.status = request.POST.get('status')
        
        try:
            tiket.jadwal = Jadwal.objects.get(pk=id_jadwal)
            tiket.save()
            messages.success(request, "Informasi tiket berhasil diperbarui!")
            return redirect('tiket_index')
        except Jadwal.DoesNotExist:
            messages.error(request, "Jadwal tidak valid.")
            
    list_jadwal = Jadwal.objects.all().select_related('bus', 'rute')
    context = {
        'username': request.session.get('admin_username'),
        'tiket': tiket,
        'list_jadwal': list_jadwal
    }
    return render(request, 'core/tiket/edit.html', context)

def tiket_delete(request, id_tiket):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    if request.method == 'POST':
        try:
            tiket = Tiket.objects.get(pk=id_tiket)
            tiket.delete()
            messages.success(request, "Tiket berhasil dihapus!")
        except Tiket.DoesNotExist:
            messages.error(request, "Tiket gagal dihapus karena tidak ditemukan.")
            
    return redirect('tiket_index')

# Pelanggan Views
def pelanggan_index(request):
    if 'admin_id' not in request.session:
        return redirect('login')
    semua_pelanggan = Pelanggan.objects.all().order_by('-id_pelanggan')
    context = {
        'username': request.session.get('admin_username'),
        'semua_pelanggan': semua_pelanggan
    }
    return render(request, 'core/pelanggan/index.html', context)

def pelanggan_add(request):
    if 'admin_id' not in request.session:
        return redirect('login')
    if request.method == 'POST':
        nama_pelanggan = request.POST.get('nama_pelanggan')
        jenis_kelamin = request.POST.get('jenis_kelamin')
        alamat = request.POST.get('alamat')
        nomor_telpon = request.POST.get('nomor_telpon')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        Pelanggan.objects.create(
            nama_pelanggan=nama_pelanggan,
            jenis_kelamin=jenis_kelamin,
            alamat=alamat,
            nomor_telpon=nomor_telpon,
            email=email,
            password=password
        )
        messages.success(request, f"Pelanggan {nama_pelanggan} berhasil ditambahkan!")
        return redirect('pelanggan_index')
        
    context = {'username': request.session.get('admin_username')}
    return render(request, 'core/pelanggan/add.html', context)

def pelanggan_edit(request, id_pelanggan):
    if 'admin_id' not in request.session:
        return redirect('login')
    try:
        pelanggan = Pelanggan.objects.get(pk=id_pelanggan)
    except Pelanggan.DoesNotExist:
        messages.error(request, "Pelanggan tidak ditemukan.")
        return redirect('pelanggan_index')
        
    if request.method == 'POST':
        pelanggan.nama_pelanggan = request.POST.get('nama_pelanggan')
        pelanggan.jenis_kelamin = request.POST.get('jenis_kelamin')
        pelanggan.alamat = request.POST.get('alamat')
        pelanggan.nomor_telpon = request.POST.get('nomor_telpon')
        pelanggan.email = request.POST.get('email')
        pelanggan.password = request.POST.get('password')
        pelanggan.save()
        messages.success(request, f"Data pelanggan {pelanggan.nama_pelanggan} berhasil diperbarui!")
        return redirect('pelanggan_index')
        
    context = {
        'username': request.session.get('admin_username'),
        'pelanggan': pelanggan
    }
    return render(request, 'core/pelanggan/edit.html', context)

def pelanggan_delete(request, id_pelanggan):
    if 'admin_id' not in request.session:
        return redirect('login')
    if request.method == 'POST':
        try:
            pelanggan = Pelanggan.objects.get(pk=id_pelanggan)
            nama_pelanggan = pelanggan.nama_pelanggan
            pelanggan.delete()
            messages.success(request, f"Pelanggan {nama_pelanggan} berhasil dihapus!")
        except Pelanggan.DoesNotExist:
            messages.error(request, "Pelanggan gagal dihapus karena tidak ditemukan.")
    return redirect('pelanggan_index')

# Pemesanan Views
def pemesanan_index(request):
    if 'admin_id' not in request.session:
        return redirect('login')
    semua_pemesanan = Pemesanan.objects.all().select_related('pelanggan', 'tiket__jadwal__rute', 'tiket__jadwal__bus').order_by('-id_pemesanan')
    context = {
        'username': request.session.get('admin_username'),
        'semua_pemesanan': semua_pemesanan
    }
    return render(request, 'core/pemesanan/index.html', context)

def pemesanan_add(request):
    if 'admin_id' not in request.session:
        return redirect('login')
    if request.method == 'POST':
        id_pelanggan = request.POST.get('id_pelanggan')
        id_tiket = request.POST.get('id_tiket')
        jumlah_tiket = request.POST.get('jumlah_tiket')
        
        try:
            pelanggan = Pelanggan.objects.get(pk=id_pelanggan)
            tiket = Tiket.objects.get(pk=id_tiket)
            
            Pemesanan.objects.create(
                pelanggan=pelanggan,
                tiket=tiket,
                jumlah_tiket=jumlah_tiket
            )
            messages.success(request, "Transaksi pemesanan tiket berhasil dibuat!")
            return redirect('pemesanan_index')
        except (Pelanggan.DoesNotExist, Tiket.DoesNotExist):
            messages.error(request, "Pelanggan atau Tiket tidak valid.")
            
    list_pelanggan = Pelanggan.objects.all()
    list_tiket = Tiket.objects.all().select_related('jadwal__rute', 'jadwal__bus')
    context = {
        'username': request.session.get('admin_username'),
        'list_pelanggan': list_pelanggan,
        'list_tiket': list_tiket
    }
    return render(request, 'core/pemesanan/add.html', context)

def pemesanan_edit(request, id_pemesanan):
    if 'admin_id' not in request.session:
        return redirect('login')
    try:
        pemesanan = Pemesanan.objects.get(pk=id_pemesanan)
    except Pemesanan.DoesNotExist:
        messages.error(request, "Transaksi pemesanan tidak ditemukan.")
        return redirect('pemesanan_index')
        
    if request.method == 'POST':
        id_pelanggan = request.POST.get('id_pelanggan')
        id_tiket = request.POST.get('id_tiket')
        pemesanan.jumlah_tiket = request.POST.get('jumlah_tiket')
        
        try:
            pemesanan.pelanggan = Pelanggan.objects.get(pk=id_pelanggan)
            pemesanan.tiket = Tiket.objects.get(pk=id_tiket)
            pemesanan.save()
            messages.success(request, "Transaksi pemesanan berhasil diperbarui!")
            return redirect('pemesanan_index')
        except (Pelanggan.DoesNotExist, Tiket.DoesNotExist):
            messages.error(request, "Pelanggan atau Tiket tidak valid.")
            
    list_pelanggan = Pelanggan.objects.all()
    list_tiket = Tiket.objects.all().select_related('jadwal__rute', 'jadwal__bus')
    context = {
        'username': request.session.get('admin_username'),
        'pemesanan': pemesanan,
        'list_pelanggan': list_pelanggan,
        'list_tiket': list_tiket
    }
    return render(request, 'core/pemesanan/edit.html', context)

def pemesanan_delete(request, id_pemesanan):
    if 'admin_id' not in request.session:
        return redirect('login')
    if request.method == 'POST':
        try:
            pemesanan = Pemesanan.objects.get(pk=id_pemesanan)
            pemesanan.delete()
            messages.success(request, "Transaksi pemesanan berhasil dihapus!")
        except Pemesanan.DoesNotExist:
            messages.error(request, "Transaksi pemesanan gagal dihapus karena tidak ditemukan.")
    return redirect('pemesanan_index')

# Pembayaran Views
def pembayaran_index(request):
    if 'admin_id' not in request.session:
        return redirect('login')
    semua_pembayaran = Pembayaran.objects.all().select_related('pelanggan').order_by('-id_pembayaran')
    context = {
        'username': request.session.get('admin_username'),
        'semua_pembayaran': semua_pembayaran
    }
    return render(request, 'core/pembayaran/index.html', context)

def pembayaran_add(request):
    if 'admin_id' not in request.session:
        return redirect('login')
    if request.method == 'POST':
        id_pelanggan = request.POST.get('id_pelanggan')
        metode_bayar = request.POST.get('metode_bayar')
        jumlah_bayar = request.POST.get('jumlah_bayar')
        status = request.POST.get('status')
        file_bukti = request.FILES.get('bukti_bayar')
        
        try:
            pelanggan = Pelanggan.objects.get(pk=id_pelanggan)
            Pembayaran.objects.create(
                pelanggan=pelanggan,
                metode_bayar=metode_bayar,
                jumlah_bayar=jumlah_bayar,
                status=status,
                bukti_bayar=file_bukti
            )
            messages.success(request, "Catatan pembayaran berhasil dibuat!")
            return redirect('pembayaran_index')
        except Pelanggan.DoesNotExist:
            messages.error(request, "Pelanggan tidak valid.")
            
    list_pelanggan = Pelanggan.objects.all()
    context = {
        'username': request.session.get('admin_username'),
        'list_pelanggan': list_pelanggan
    }
    return render(request, 'core/pembayaran/add.html', context)

def pembayaran_edit(request, id_pembayaran):
    if 'admin_id' not in request.session:
        return redirect('login')
    try:
        pembayaran = Pembayaran.objects.get(pk=id_pembayaran)
    except Pembayaran.DoesNotExist:
        messages.error(request, "Catatan pembayaran tidak ditemukan.")
        return redirect('pembayaran_index')
        
    if request.method == 'POST':
        id_pelanggan = request.POST.get('id_pelanggan')
        pembayaran.metode_bayar = request.POST.get('metode_bayar')
        pembayaran.jumlah_bayar = request.POST.get('jumlah_bayar')
        pembayaran.status = request.POST.get('status')
        
        file_bukti = request.FILES.get('bukti_bayar')
        if file_bukti:
            pembayaran.bukti_bayar = file_bukti
            
        try:
            pembayaran.pelanggan = Pelanggan.objects.get(pk=id_pelanggan)
            pembayaran.save()
            messages.success(request, "Catatan pembayaran berhasil diperbarui!")
            return redirect('pembayaran_index')
        except Pelanggan.DoesNotExist:
            messages.error(request, "Pelanggan tidak valid.")
            
    list_pelanggan = Pelanggan.objects.all()
    context = {
        'username': request.session.get('admin_username'),
        'pembayaran': pembayaran,
        'list_pelanggan': list_pelanggan
    }
    return render(request, 'core/pembayaran/edit.html', context)

def pembayaran_delete(request, id_pembayaran):
    if 'admin_id' not in request.session:
        return redirect('login')
    if request.method == 'POST':
        try:
            pembayaran = Pembayaran.objects.get(pk=id_pembayaran)
            pembayaran.delete()
            messages.success(request, "Catatan pembayaran berhasil dihapus!")
        except Pembayaran.DoesNotExist:
            messages.error(request, "Catatan pembayaran gagal dihapus karena tidak ditemukan.")
    return redirect('pembayaran_index')

# Portal Publik Views
def public_home(request):
    list_asal = Rute.objects.values_list('kota_asal', flat=True).distinct().order_by('kota_asal')
    list_tujuan = Rute.objects.values_list('kota_tujuan', flat=True).distinct().order_by('kota_tujuan')
    daftar_bus = Bus.objects.all().order_by('-id_bus')
    daftar_tiket = Tiket.objects.filter(status='Tersedia').select_related('jadwal__rute', 'jadwal__bus')[:6]
    
    context = {
        'list_asal': list_asal,
        'list_tujuan': list_tujuan,
        'daftar_bus': daftar_bus,
        'daftar_tiket': daftar_tiket,
    }
    return render(request, 'core/publik/home.html', context)

def public_search(request):
    asal = request.GET.get('asal')
    tujuan = request.GET.get('tujuan')
    tanggal = request.GET.get('tanggal')
    
    # Filter jadwal yang cocok dengan asal, tujuan, dan tanggal
    jadwal_list = Jadwal.objects.filter(
        rute__kota_asal=asal,
        rute__kota_tujuan=tujuan,
        tanggal_berangkat=tanggal
    )
    
    # Ambil tiket terkait
    tiket_list = Tiket.objects.filter(jadwal__in=jadwal_list).select_related('jadwal__rute', 'jadwal__bus')
    
    context = {
        'tiket_list': tiket_list,
        'asal': asal,
        'tujuan': tujuan,
        'tanggal': tanggal,
    }
    return render(request, 'core/publik/search_results.html', context)

@transaction.atomic
def public_checkout(request, id_tiket):
    # Proteksi Session Pelanggan
    if 'pelanggan_id' not in request.session:
        messages.error(request, "Silakan login terlebih dahulu untuk memesan tiket!")
        return redirect('pelanggan_login')
        
    try:
        tiket = Tiket.objects.select_related('jadwal__rute', 'jadwal__bus').get(pk=id_tiket)
    except Tiket.DoesNotExist:
        messages.error(request, "Tiket tidak ditemukan atau sudah tidak berlaku.")
        return redirect('public_home')
        
    # Ambil pelanggan dari session
    pelanggan = Pelanggan.objects.get(pk=request.session['pelanggan_id'])
        
    pesanan_terbit = Pemesanan.objects.filter(tiket_id=id_tiket)
    kursi_terpesan = []
    for p in pesanan_terbit:
        if p.nomor_kursi:
            kursi_terpesan.extend([k.strip() for k in p.nomor_kursi.split(',')])
            
    if request.method == 'POST':
        jumlah_tiket = int(request.POST.get('jumlah_tiket', 1))
        metode_bayar = 'Online'
        nomor_kursi = request.POST.get('nomor_kursi')
        pakai_bagasi = request.POST.get('layanan_bagasi') == 'yes'
        
        # a. Buat record Pemesanan baru menggunakan pelanggan yang login
        pemesanan = Pemesanan.objects.create(
            pelanggan=pelanggan,
            tiket=tiket,
            jumlah_tiket=jumlah_tiket,
            nomor_kursi=nomor_kursi,
            layanan_bagasi=pakai_bagasi
        )
        
        # b. Hitung total bayar dan buat record Pembayaran baru (Pending)
        biaya_dasar = jumlah_tiket * tiket.harga_tiket
        biaya_bagasi = 50000 if pakai_bagasi else 0
        total_bayar = biaya_dasar + biaya_bagasi
        status_default = 'Pending'
        order_id = f"GM-{pemesanan.id_pemesanan}-{int(time.time())}"
        
        pembayaran = Pembayaran.objects.create(
            pelanggan=pelanggan,
            metode_bayar=metode_bayar,
            jumlah_bayar=total_bayar,
            status=status_default,
            order_id=order_id
        )
        
        snap = midtransclient.Snap(
            is_production=settings.MIDTRANS_IS_PRODUCTION,
            server_key=settings.MIDTRANS_SERVER_KEY,
            client_key=settings.MIDTRANS_CLIENT_KEY
        )
        param = {
            "transaction_details": { "order_id": order_id, "gross_amount": int(total_bayar) },
            "customer_details": {
                "first_name": pelanggan.nama_pelanggan,
                "email": pelanggan.email or "guest@gunungmas.com",
                "phone": pelanggan.nomor_telpon
            }
        }
        transaction = snap.create_transaction(param)
        pembayaran.snap_token = transaction['token']
        pembayaran.save()
        
        # c. SweetAlert2 success message
        messages.success(request, f"Pemesanan atas nama {pelanggan.nama_pelanggan} berhasil dibuat! Silakan lakukan pembayaran.")
        return redirect('public_invoice', id_pemesanan=pemesanan.id_pemesanan)
        
    context = {
        'tiket': tiket,
        'pelanggan': pelanggan,
        'kursi_terpesan': kursi_terpesan
    }
    return render(request, 'core/publik/checkout.html', context)

def public_invoice(request, id_pemesanan):
    # Proteksi Session Pelanggan
    if 'pelanggan_id' not in request.session:
        messages.error(request, "Silakan login terlebih dahulu untuk mengakses invoice!")
        return redirect('pelanggan_login')
        
    try:
        pemesanan = Pemesanan.objects.select_related('pelanggan', 'tiket__jadwal__rute', 'tiket__jadwal__bus').get(pk=id_pemesanan)
        pembayaran = Pembayaran.objects.filter(order_id__icontains=f"GM-{id_pemesanan}-").last()
    except Pemesanan.DoesNotExist:
        messages.error(request, "Transaksi tidak ditemukan.")
        return redirect('public_home')
        
    context = {
        'pemesanan': pemesanan,
        'pembayaran': pembayaran,
        'client_key': settings.MIDTRANS_CLIENT_KEY
    }
    return render(request, 'core/publik/invoice.html', context)

# Autentikasi Pelanggan Views
def pelanggan_register(request):
    if 'pelanggan_id' in request.session:
        return redirect('public_home')
        
    if request.method == 'POST':
        nama_pelanggan = request.POST.get('nama_pelanggan')
        jenis_kelamin = request.POST.get('jenis_kelamin')
        alamat = request.POST.get('alamat')
        nomor_telpon = request.POST.get('nomor_telpon')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Cek apakah email sudah terdaftar
        if Pelanggan.objects.filter(email=email).exists():
            messages.error(request, "Email sudah terdaftar! Silakan gunakan email lain.")
            return render(request, 'core/publik/register.html')
            
        # Simpan pelanggan baru
        Pelanggan.objects.create(
            nama_pelanggan=nama_pelanggan,
            jenis_kelamin=jenis_kelamin,
            alamat=alamat,
            nomor_telpon=nomor_telpon,
            email=email,
            password=password # Plain text sesuai kesepakatan
        )
        messages.success(request, "Registrasi berhasil! Silakan login untuk melanjutkan.")
        return redirect('pelanggan_login')
        
    return render(request, 'core/publik/register.html')

def pelanggan_login(request):
    if 'pelanggan_id' in request.session:
        return redirect('public_home')
        
    if request.method == 'POST':
        email_input = request.POST.get('email')
        pass_input = request.POST.get('password')
        
        try:
            # Query manual ke model Pelanggan kustom
            pelanggan = Pelanggan.objects.get(email=email_input, password=pass_input)
            
            # Set Session
            request.session['pelanggan_id'] = pelanggan.id_pelanggan
            request.session['pelanggan_nama'] = pelanggan.nama_pelanggan
            
            messages.success(request, f"Selamat datang kembali, {pelanggan.nama_pelanggan}!")
            return redirect('public_home')
            
        except Pelanggan.DoesNotExist:
            messages.error(request, "Email atau password salah!")
            return render(request, 'core/publik/login.html')
            
    return render(request, 'core/publik/login.html')

def pelanggan_logout(request):
    request.session.pop('pelanggan_id', None)
    request.session.pop('pelanggan_nama', None)
    messages.success(request, "Anda telah berhasil keluar dari akun Penumpang.")
    return redirect('public_home')

def pelanggan_riwayat(request):
    if 'pelanggan_id' not in request.session:
        messages.error(request, "Silakan login terlebih dahulu untuk mengakses riwayat pemesanan!")
        return redirect('pelanggan_login')
        
    riwayat = Pemesanan.objects.filter(
        pelanggan_id=request.session['pelanggan_id']
    ).select_related('tiket__jadwal__rute', 'tiket__jadwal__bus').order_by('-id_pemesanan')
    
    # Ambil pembayaran pelanggan secara berurutan untuk dipetakan secara 1-to-1
    pembayaran_list = list(Pembayaran.objects.filter(
        pelanggan_id=request.session['pelanggan_id']
    ).order_by('-id_pembayaran'))
    
    for i, r in enumerate(riwayat):
        if i < len(pembayaran_list):
            r.pembayaran = pembayaran_list[i]
        else:
            r.pembayaran = None
        
    context = {
        'riwayat': riwayat
    }
    return render(request, 'core/publik/riwayat.html', context)

def pelanggan_profil(request):
    if 'pelanggan_id' not in request.session:
        messages.error(request, "Silakan login terlebih dahulu untuk mengakses profil Anda!")
        return redirect('pelanggan_login')
        
    pelanggan = Pelanggan.objects.get(pk=request.session['pelanggan_id'])
    
    if request.method == 'POST':
        nama_pelanggan = request.POST.get('nama_pelanggan')
        jenis_kelamin = request.POST.get('jenis_kelamin')
        alamat = request.POST.get('alamat')
        nomor_telpon = request.POST.get('nomor_telpon')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Validasi Email Unik
        if Pelanggan.objects.filter(email=email).exclude(pk=pelanggan.pk).exists():
            messages.error(request, "Email sudah digunakan oleh akun lain!")
            return redirect('pelanggan_profil')
            
        # Update fields
        pelanggan.nama_pelanggan = nama_pelanggan
        pelanggan.jenis_kelamin = jenis_kelamin
        pelanggan.alamat = alamat
        pelanggan.nomor_telpon = nomor_telpon
        pelanggan.email = email
        pelanggan.password = password
        pelanggan.save()
        
        # Update session
        request.session['pelanggan_nama'] = pelanggan.nama_pelanggan
        
        messages.success(request, "Profil Anda berhasil diperbarui!")
        return redirect('pelanggan_profil')
        
    context = {
        'pelanggan': pelanggan
    }
    return render(request, 'core/publik/profil.html', context)


# Helper xhtml2pdf untuk static/media file resolution
def link_callback(uri, rel):
    """
    Mengonversi URL relatif/dinamis Django (static & media) menjadi path berkas fisik lokal 
    yang dapat dibaca secara absolut oleh engine xhtml2pdf/ReportLab.
    """
    import os
    from django.conf import settings
    
    # Jika URI mengandung STATIC_URL
    if uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.BASE_DIR, uri.replace(settings.STATIC_URL, "static/"))
    # Jika URI mengandung MEDIA_URL
    elif uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    else:
        return uri

    # Pastikan file fisik benar-benar ada di penyimpanan server lokal
    if not os.path.isfile(path):
        # Kembalikan string URI asal agar pembacaan tidak macet (jangan mengembalikan None/NotImplemented)
        return uri
        
    return path


# Fungsi Helper untuk memetakan Pemesanan ke Pembayaran secara 1-to-1
def get_pemesanan_with_pembayaran(start_date=None, end_date=None, status_bayar=None):
    pemesanan_qs = Pemesanan.objects.all().select_related('pelanggan', 'tiket__jadwal__rute', 'tiket__jadwal__bus').order_by('-id_pemesanan')
    if start_date:
        pemesanan_qs = pemesanan_qs.filter(tanggal_pesan__gte=start_date)
    if end_date:
        pemesanan_qs = pemesanan_qs.filter(tanggal_pesan__lte=end_date)
        
    pembayaran_qs = Pembayaran.objects.all().select_related('pelanggan').order_by('-id_pembayaran')
    
    # Kelompokkan pemesanan berdasarkan pelanggan_id
    pemesanan_by_pelanggan = {}
    for p in pemesanan_qs:
        pemesanan_by_pelanggan.setdefault(p.pelanggan_id, []).append(p)
        
    # Kelompokkan pembayaran berdasarkan pelanggan_id
    pembayaran_by_pelanggan = {}
    for pb in pembayaran_qs:
        pembayaran_by_pelanggan.setdefault(pb.pelanggan_id, []).append(pb)
        
    # Petakan secara berurutan (1-to-1)
    result = []
    for p_id, p_list in pemesanan_by_pelanggan.items():
        pb_list = pembayaran_by_pelanggan.get(p_id, [])
        for i, p in enumerate(p_list):
            if i < len(pb_list):
                p.pembayaran = pb_list[i]
            else:
                p.pembayaran = None
                
            # Filter berdasarkan status_bayar jika diatur
            if status_bayar:
                if p.pembayaran and p.pembayaran.status == status_bayar:
                    result.append(p)
            else:
                result.append(p)
                
    # Urutkan hasil akhir berdasarkan id_pemesanan descending
    result.sort(key=lambda x: x.id_pemesanan, reverse=True)
    return result


# View Laporan Pelanggan (Preview HTML)
def laporan_pelanggan(request):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    jenis_kelamin = request.GET.get('jenis_kelamin')
    keyword_nama = request.GET.get('keyword_nama')
    
    data = Pelanggan.objects.all()
    if jenis_kelamin:
        data = data.filter(jenis_kelamin=jenis_kelamin)
    if keyword_nama:
        data = data.filter(nama_pelanggan__icontains=keyword_nama)
        
    context = {
        'username': request.session.get('admin_username'),
        'data': data,
        'jenis_kelamin': jenis_kelamin,
        'keyword_nama': keyword_nama,
    }
    return render(request, 'core/laporan/pelanggan.html', context)


# View Laporan Bus & Rute (Preview HTML)
def laporan_bus_rute(request):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    tipe_bus = request.GET.get('tipe_bus')
    
    data = Bus.objects.all()
    if tipe_bus:
        data = data.filter(tipe_bus=tipe_bus)
        
    context = {
        'username': request.session.get('admin_username'),
        'data': data,
        'tipe_bus': tipe_bus,
    }
    return render(request, 'core/laporan/bus_rute.html', context)


# View Laporan Pemesanan & Pembayaran (Preview HTML)
def laporan_pemesanan_pembayaran(request):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status_bayar = request.GET.get('status_bayar')
    
    data = get_pemesanan_with_pembayaran(start_date=start_date, end_date=end_date, status_bayar=status_bayar)
    
    context = {
        'username': request.session.get('admin_username'),
        'data': data,
        'start_date': start_date,
        'end_date': end_date,
        'status_bayar': status_bayar,
    }
    return render(request, 'core/laporan/pemesanan_pembayaran.html', context)


# View Laporan Jadwal & Tiket (Preview HTML)
def laporan_jadwal_tiket(request):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    status_tiket = request.GET.get('status_tiket')
    
    data = Tiket.objects.all().select_related('jadwal__rute', 'jadwal__bus').order_by('-id_tiket')
    if status_tiket:
        data = data.filter(status=status_tiket)
        
    context = {
        'username': request.session.get('admin_username'),
        'data': data,
        'status_tiket': status_tiket,
    }
    return render(request, 'core/laporan/jadwal_tiket.html', context)


# View Laporan Pendapatan Bersih (Preview HTML)
def laporan_pendapatan(request):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    pemesanan_list = get_pemesanan_with_pembayaran(start_date=start_date, end_date=end_date)
    data = []
    total_pendapatan = 0
    for p in pemesanan_list:
        if p.pembayaran and p.pembayaran.status == 'Lunas':
            data.append(p)
            total_pendapatan += p.pembayaran.jumlah_bayar
            
    context = {
        'username': request.session.get('admin_username'),
        'data': data,
        'total_pendapatan': total_pendapatan,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'core/laporan/pendapatan.html', context)


# View Laporan Unduh PDF (xhtml2pdf)
def laporan_unduh_pdf(request, jenis_laporan):
    if 'admin_id' not in request.session:
        return redirect('login')
        
    from datetime import datetime
    waktu_cetak = datetime.now().strftime('%d %B %Y %H:%M') + " WITA"
    
    # Replikasi parameter filter
    jenis_kelamin = request.GET.get('jenis_kelamin')
    keyword_nama = request.GET.get('keyword_nama')
    tipe_bus = request.GET.get('tipe_bus')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status_bayar = request.GET.get('status_bayar')
    status_tiket = request.GET.get('status_tiket')
    
    data = []
    total_pendapatan = 0
    
    if jenis_laporan == 'pelanggan':
        data = Pelanggan.objects.all()
        if jenis_kelamin:
            data = data.filter(jenis_kelamin=jenis_kelamin)
        if keyword_nama:
            data = data.filter(nama_pelanggan__icontains=keyword_nama)
            
    elif jenis_laporan == 'bus_rute':
        data = Bus.objects.all()
        if tipe_bus:
            data = data.filter(tipe_bus=tipe_bus)
            
    elif jenis_laporan == 'pemesanan_pembayaran':
        data = get_pemesanan_with_pembayaran(start_date=start_date, end_date=end_date, status_bayar=status_bayar)
        
    elif jenis_laporan == 'jadwal_tiket':
        data = Tiket.objects.all().select_related('jadwal__rute', 'jadwal__bus').order_by('-id_tiket')
        if status_tiket:
            data = data.filter(status=status_tiket)
            
    elif jenis_laporan == 'pendapatan':
        pemesanan_list = get_pemesanan_with_pembayaran(start_date=start_date, end_date=end_date)
        for p in pemesanan_list:
            if p.pembayaran and p.pembayaran.status == 'Lunas':
                data.append(p)
                total_pendapatan += p.pembayaran.jumlah_bayar
                
    context = {
        'jenis_laporan': jenis_laporan,
        'data': data,
        'total_pendapatan': total_pendapatan,
        'waktu_cetak': waktu_cetak,
    }
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Laporan_{jenis_laporan}.pdf"'
    
    template = get_template('core/laporan/pdf_template.html')
    html_content = template.render(context)
    
    pisa_status = pisa.CreatePDF(html_content, dest=response, link_callback=link_callback)
    
    if pisa_status.err:
        return HttpResponse('Gagal membuat PDF: <pre>' + html_content + '</pre>')
    return response

@csrf_exempt
def midtrans_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = data.get('order_id')
            transaction_status = data.get('transaction_status')
            
            pembayaran = Pembayaran.objects.get(order_id=order_id)
            
            if transaction_status in ['capture', 'settlement']:
                pembayaran.status = 'Lunas'
                pembayaran.save()
                
                try:
                    # Proteksi pembacaan order_id format: GM-{id_pemesanan}-{timestamp}
                    order_parts = pembayaran.order_id.split('-')
                    if len(order_parts) >= 2:
                        id_pesan = order_parts[1]
                        pemesanan = Pemesanan.objects.select_related('pelanggan', 'tiket__jadwal__rute', 'tiket__jadwal__bus').get(pk=id_pesan)
                        
                        # Gabungkan semua data manifest termasuk status layanan_bagasi secara eksplisit
                        status_bagasi_str = "Ya" if pemesanan.layanan_bagasi else "Tidak"
                        kursi_str = pemesanan.nomor_kursi if pemesanan.nomor_kursi else "-"
                        
                        pesan_raw = f"VALID|{pemesanan.id_pemesanan}|{pemesanan.pelanggan.nama_pelanggan}|{kursi_str}|Bagasi:{status_bagasi_str}"
                        pesan_asli = pesan_raw.encode('utf-8')
                        
                        # Proses Enkripsi QR Code menggunakan kunci dari settings
                        f = Fernet(settings.TICKET_CRYPT_KEY)
                        pesan_enkripsi = f.encrypt(pesan_asli)
                        
                        # Pembuatan berkas QR Code PNG
                        qr = qrcode.QRCode(version=1, box_size=10, border=5)
                        qr.add_data(pesan_enkripsi.decode('utf-8'))
                        qr.make(fit=True)
                        img = qr.make_image(fill='black', back_color='white')
                        
                        buffer = BytesIO()
                        img.save(buffer, format="PNG")
                        file_name = f'qr_ticket_{pemesanan.id_pemesanan}.png'
                        
                        # Simpan QR Code ke media storage
                        if pemesanan.qr_code:
                            pemesanan.qr_code.delete(save=False)
                        pemesanan.qr_code.save(file_name, File(buffer), save=True)
                except Exception as qr_err:
                    print("Gagal generate QR terenkripsi di Webhook:", str(qr_err))
            elif transaction_status in ['deny', 'cancel', 'expire']:
                pembayaran.status = 'Dibatalkan'
                pembayaran.save()
            elif transaction_status == 'pending':
                pembayaran.status = 'Pending'
                pembayaran.save()
            return HttpResponse("OK", status=200)
        except Exception as e:
            return HttpResponse(str(e), status=500)
    return HttpResponse("Method Not Allowed", status=405)

def admin_scan_tiket(request):
    if 'admin_id' not in request.session:
        messages.error(request, "Silakan login terlebih dahulu.")
        return redirect('login')
    return render(request, 'core/admin/scanner.html')

@csrf_exempt
def api_verify_qr(request):
    if request.method == 'POST':
        try:
            import json
            from django.http import JsonResponse
            from django.conf import settings
            from cryptography.fernet import Fernet
            from .models import Pemesanan

            data = json.loads(request.body)
            qr_text = data.get('qr_text')
            
            f = Fernet(settings.TICKET_CRYPT_KEY)
            decrypted = f.decrypt(qr_text.encode('utf-8')).decode('utf-8')
            
            parts = decrypted.split('|')
            if len(parts) >= 4 and parts[0] == 'VALID':
                id_pemesanan = parts[1]
                pemesanan = Pemesanan.objects.get(pk=id_pemesanan)
                
                pemesanan.status_hadir = 'Sudah di Bus'
                pemesanan.save()
                
                # Baca parameter ke-5 jika ada, jika tidak pakai nilai fallback aman
                info_bagasi = parts[4] if len(parts) >= 5 else "Bagasi: Tidak"
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Tiket Valid & Penumpang Berhasil Boarding!',
                    'id_pemesanan': id_pemesanan,
                    'nama_pelanggan': parts[2],
                    'nomor_kursi': parts[3],
                    'bagasi': info_bagasi,
                    'status_hadir': pemesanan.status_hadir
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Format tiket tidak valid.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': 'Tiket Palsu atau Tidak Dikenali.'})
    return JsonResponse({'status': 'error', 'message': 'Method Not Allowed'})

def sopir_login_view(request):
    if 'sopir_id' in request.session:
        return redirect('sopir_dashboard')
    if request.method == 'POST':
        lisensi = request.POST.get('nomor_lisensi')
        pwd = request.POST.get('password')
        try:
            sopir = Sopir.objects.get(nomor_lisensi=lisensi, password=pwd)
            request.session['sopir_id'] = sopir.id_sopir
            request.session['sopir_nama'] = sopir.nama_sopir
            messages.success(request, f"Selamat bertugas, Kapten {sopir.nama_sopir}!")
            return redirect('sopir_dashboard')
        except Sopir.DoesNotExist:
            messages.error(request, "Nomor lisensi (SIM) atau password salah!")
    return render(request, 'core/sopir_portal/login.html')

def sopir_logout_view(request):
    request.session.pop('sopir_id', None)
    request.session.pop('sopir_nama', None)
    messages.success(request, "Berhasil keluar dari sistem portal sopir.")
    return redirect('sopir_login')

def sopir_dashboard(request):
    if 'sopir_id' not in request.session:
        messages.error(request, "Silakan login terlebih dahulu.")
        return redirect('sopir_login')
    
    sopir_id = request.session['sopir_id']
    bus = Bus.objects.filter(sopir_id=sopir_id).first()
    
    jadwal_aktif = []
    total_tiket = 0
    if bus:
        from datetime import date
        jadwal_aktif = Jadwal.objects.filter(bus=bus, tanggal_berangkat__gte=date.today()).order_by('tanggal_berangkat', 'jam_berangkat')
        
        # Hitung tiket terjual untuk jadwal-jadwal tersebut
        jadwal_ids = [j.id_jadwal for j in jadwal_aktif]
        if jadwal_ids:
            pemesanan_lunas = Pemesanan.objects.filter(
                tiket__jadwal__in=jadwal_ids,
                pembayaran__status='Lunas'
            ).distinct()
            total_tiket = sum(p.jumlah_tiket for p in pemesanan_lunas)
            
    context = {
        'bus': bus,
        'jadwal_aktif': jadwal_aktif,
        'total_tiket': total_tiket
    }
    return render(request, 'core/sopir_portal/dashboard.html', context)
