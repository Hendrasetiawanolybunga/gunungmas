from django.urls import path
from . import views

urlpatterns = [
    # Auth System (Manual)
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard & Main Admin Panel
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Kelola Bus (Contoh CRUD awal)
    path('dashboard/bus/', views.bus_index, name='bus_index'),
    path('dashboard/bus/add/', views.bus_add, name='bus_add'),
    path('dashboard/bus/edit/<int:id_bus>/', views.bus_edit, name='bus_edit'),
    path('dashboard/bus/delete/<int:id_bus>/', views.bus_delete, name='bus_delete'),
    
    # Kelola Rute
    path('dashboard/rute/', views.rute_index, name='rute_index'),
    path('dashboard/rute/add/', views.rute_add, name='rute_add'),
    path('dashboard/rute/edit/<int:id_rute>/', views.rute_edit, name='rute_edit'),
    path('dashboard/rute/delete/<int:id_rute>/', views.rute_delete, name='rute_delete'),

    # Kelola Sopir
    path('dashboard/sopir/', views.sopir_index, name='sopir_index'),
    path('dashboard/sopir/add/', views.sopir_add, name='sopir_add'),
    path('dashboard/sopir/edit/<int:id_sopir>/', views.sopir_edit, name='sopir_edit'),
    path('dashboard/sopir/delete/<int:id_sopir>/', views.sopir_delete, name='sopir_delete'),

    # Jadwal
    path('dashboard/jadwal/', views.jadwal_index, name='jadwal_index'),
    path('dashboard/jadwal/add/', views.jadwal_add, name='jadwal_add'),
    path('dashboard/jadwal/edit/<int:id_jadwal>/', views.jadwal_edit, name='jadwal_edit'),
    path('dashboard/jadwal/delete/<int:id_jadwal>/', views.jadwal_delete, name='jadwal_delete'),

    # Tiket
    path('dashboard/tiket/', views.tiket_index, name='tiket_index'),
    path('dashboard/tiket/add/', views.tiket_add, name='tiket_add'),
    path('dashboard/tiket/edit/<int:id_tiket>/', views.tiket_edit, name='tiket_edit'),
    path('dashboard/tiket/delete/<int:id_tiket>/', views.tiket_delete, name='tiket_delete'),

    # Pelanggan
    path('dashboard/pelanggan/', views.pelanggan_index, name='pelanggan_index'),
    path('dashboard/pelanggan/add/', views.pelanggan_add, name='pelanggan_add'),
    path('dashboard/pelanggan/edit/<int:id_pelanggan>/', views.pelanggan_edit, name='pelanggan_edit'),
    path('dashboard/pelanggan/delete/<int:id_pelanggan>/', views.pelanggan_delete, name='pelanggan_delete'),

    # Pemesanan
    path('dashboard/pemesanan/', views.pemesanan_index, name='pemesanan_index'),
    path('dashboard/pemesanan/add/', views.pemesanan_add, name='pemesanan_add'),
    path('dashboard/pemesanan/edit/<int:id_pemesanan>/', views.pemesanan_edit, name='pemesanan_edit'),
    path('dashboard/pemesanan/delete/<int:id_pemesanan>/', views.pemesanan_delete, name='pemesanan_delete'),

    # Pembayaran
    path('dashboard/pembayaran/', views.pembayaran_index, name='pembayaran_index'),
    path('dashboard/pembayaran/add/', views.pembayaran_add, name='pembayaran_add'),
    path('dashboard/pembayaran/edit/<int:id_pembayaran>/', views.pembayaran_edit, name='pembayaran_edit'),
    path('dashboard/pembayaran/delete/<int:id_pembayaran>/', views.pembayaran_delete, name='pembayaran_delete'),

    # Portal Publik
    path('home/', views.public_home, name='public_home'),
    path('cari-tiket/', views.public_search, name='public_search'),
    path('pesan-tiket/<int:id_tiket>/', views.public_checkout, name='public_checkout'),
    path('invoice/<int:id_pemesanan>/', views.public_invoice, name='public_invoice'),
    path('api/payment/webhook/', views.midtrans_webhook, name='midtrans_webhook'),
    
    # Autentikasi Pelanggan
    path('pelanggan/login/', views.pelanggan_login, name='pelanggan_login'),
    path('pelanggan/register/', views.pelanggan_register, name='pelanggan_register'),
    path('pelanggan/logout/', views.pelanggan_logout, name='pelanggan_logout'),
    path('riwayat-pemesanan/', views.pelanggan_riwayat, name='pelanggan_riwayat'),
    path('pelanggan/profil/', views.pelanggan_profil, name='pelanggan_profil'),

    # Fitur Laporan Admin (Preview HTML)
    path('dashboard/laporan/pelanggan/', views.laporan_pelanggan, name='laporan_pelanggan'),
    path('dashboard/laporan/bus-rute/', views.laporan_bus_rute, name='laporan_bus_rute'),
    path('dashboard/laporan/pemesanan-pembayaran/', views.laporan_pemesanan_pembayaran, name='laporan_pemesanan_pembayaran'),
    path('dashboard/laporan/jadwal-tiket/', views.laporan_jadwal_tiket, name='laporan_jadwal_tiket'),
    path('dashboard/laporan/pendapatan/', views.laporan_pendapatan, name='laporan_pendapatan'),

    # Fitur Unduh PDF (xhtml2pdf)
    path('dashboard/laporan/unduh/<str:jenis_laporan>/', views.laporan_unduh_pdf, name='laporan_unduh_pdf'),
    
    # Scanner Loket
    path('dashboard/scan/', views.admin_scan_tiket, name='admin_scan_tiket'),
    path('api/verify-qr/', views.api_verify_qr, name='api_verify_qr'),

    # Portal Sopir
    path('sopir/login/', views.sopir_login_view, name='sopir_login'),
    path('sopir/logout/', views.sopir_logout_view, name='sopir_logout'),
    path('sopir/dashboard/', views.sopir_dashboard, name='sopir_dashboard'),
    path('sopir/profil/', views.sopir_profil_view, name='sopir_profil'),
]
