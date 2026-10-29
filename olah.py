"""Logika pengolahan data (terpisah dari tampilan agar bisa diuji sendiri)."""
import pandas as pd

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]
BULAN_S = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
JENIS_HARI = ["Hari kerja", "Akhir pekan", "Libur nasional"]
OUTLET = ["Malioboro", "Wijilan", "Kaliurang", "Godean"]
KANAL = ["Makan di tempat", "Bawa pulang", "Pesan antar online"]

WAJIB = ["Tanggal", "Hari", "Jenis_Hari", "Outlet", "Kanal_Penjualan", "Jumlah_Transaksi",
         "Transaksi_Wisatawan", "Transaksi_Lokal", "Omzet_Gudeg_Rp", "Omzet_Oleh_Oleh_Rp",
         "Diskon_Rp", "Omzet_Bersih_Rp", "Rating_Rata_rata", "Jumlah_Ulasan"]


def turunan(df: pd.DataFrame) -> pd.DataFrame:
    """Tambah kolom turunan. Rasio tidak disimpan per baris; selalu dihitung dari jumlah."""
    df = df.copy()
    df["Tanggal"] = pd.to_datetime(df["Tanggal"])
    df["Bulan_No"] = df["Tanggal"].dt.month
    df["Bulan"] = df["Bulan_No"].map(lambda m: BULAN[m - 1])
    df["Pekan"] = df["Tanggal"].dt.to_period("W-SUN").dt.start_time
    df["Kuartal"] = "K" + df["Tanggal"].dt.quarter.astype(str)
    df["Rating_x_Ulasan"] = df["Rating_Rata_rata"].fillna(0) * df["Jumlah_Ulasan"]
    return df


def muat(sumber) -> pd.DataFrame:
    """Baca CSV (hasil transformasi) atau XLSX (sheet Data_Penjualan), lalu validasi kolom."""
    nama = getattr(sumber, "name", str(sumber)).lower()
    if nama.endswith((".xlsx", ".xlsm")):
        df = pd.read_excel(sumber, sheet_name="Data_Penjualan")
    else:
        df = pd.read_csv(sumber)
    hilang = [c for c in WAJIB if c not in df.columns]
    if hilang:
        raise ValueError("Kolom wajib tidak ditemukan: " + ", ".join(hilang))
    return turunan(df)


def saring(df, outlet, kanal, jenis, tgl_awal, tgl_akhir):
    m = (df.Outlet.isin(outlet) & df.Kanal_Penjualan.isin(kanal) & df.Jenis_Hari.isin(jenis)
         & df.Tanggal.between(pd.Timestamp(tgl_awal), pd.Timestamp(tgl_akhir)))
    return df[m]


def ringkas(df) -> dict:
    """KPI. Semua rasio = jumlah pembilang / jumlah penyebut."""
    t = int(df.Jumlah_Transaksi.sum())
    w = int(df.Transaksi_Wisatawan.sum())
    om = int(df.Omzet_Bersih_Rp.sum())
    u = int(df.Jumlah_Ulasan.sum())
    return dict(
        omzet=om, trx=t, wis=w, lokal=t - w, ulasan=u,
        hari=int(df.Tanggal.nunique()),
        avg=om / t if t else 0.0,
        rating=df.Rating_x_Ulasan.sum() / u if u else None,
        pangsa=w / t * 100 if t else 0.0,
        oleh=int(df.Omzet_Oleh_Oleh_Rp.sum()), diskon=int(df.Diskon_Rp.sum()),
    )


def agregat(df, kolom) -> pd.DataFrame:
    """Agregasi per kelompok; pangsa dihitung dari jumlah (bukan rata-rata rasio harian)."""
    g = df.groupby(kolom, observed=True).agg(
        trx=("Jumlah_Transaksi", "sum"), wis=("Transaksi_Wisatawan", "sum"),
        omzet=("Omzet_Bersih_Rp", "sum"), ru=("Rating_x_Ulasan", "sum"),
        ulasan=("Jumlah_Ulasan", "sum"), hari=("Tanggal", "nunique"),
    )
    g["lokal"] = g.trx - g.wis
    g["pangsa"] = (g.wis / g.trx * 100).where(g.trx > 0)
    g["rating"] = (g.ru / g.ulasan).where(g.ulasan > 0)
    return g


def per_hari(df, kolom) -> pd.DataFrame:
    """Rata-rata transaksi per hari menurut kelompok (jumlah / banyak hari pada kelompok itu)."""
    g = agregat(df, kolom)
    g["wis_hari"] = g.wis / g.hari
    g["lokal_hari"] = g.lokal / g.hari
    return g
