from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import olah

st.set_page_config(page_title="Dashboard Gudeg Sekar Arum", page_icon="🍛", layout="wide")

WIS, LOK = "#D95F02", "#1F6FB5"   # konsisten dengan D3: oranye = wisatawan, biru = lokal
DATA_BAWAAN = Path(__file__).parent / "D2_data_transformasi.csv"


# ---------------------------------------------------------------- format angka (gaya Indonesia)
def nf(x):
    return f"{x:,.0f}".replace(",", ".")


def dec(x, n=1):
    return f"{x:,.{n}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def rp(x):
    a = abs(x)
    if a >= 1e9:
        return f"Rp{dec(x / 1e9, 2)} miliar"
    if a >= 1e6:
        return f"Rp{dec(x / 1e6, 1)} juta"
    return f"Rp{nf(x)}"


def p1(x):
    return dec(x, 1) + "%"


# ---------------------------------------------------------------- data
@st.cache_data(show_spinner=False)
def baca_bawaan():
    return olah.muat(DATA_BAWAAN)


@st.cache_data(show_spinner=False)
def baca_unggahan(isi: bytes, nama: str):
    import io
    b = io.BytesIO(isi)
    b.name = nama
    return olah.muat(b)


st.markdown(
    f"""<style>
.block-container{{padding-top:2rem;max-width:1250px}}
.eyebrow{{font-size:11px;letter-spacing:.09em;text-transform:uppercase;opacity:.65;font-weight:600}}
.sw{{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 6px 0 14px}}
.insight{{border-left:3px solid {WIS};background:rgba(217,95,2,.10);padding:12px 16px;border-radius:0 8px 8px 0}}
.insight ul{{margin:6px 0 0;padding-left:18px}}
.sub{{font-size:13px;opacity:.75;margin:-4px 0 6px}}
[data-testid="stMetricValue"]{{font-size:1.65rem}}
</style>""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- sidebar: sumber data + filter
with st.sidebar:
    st.header("Filter")
    unggah = st.file_uploader("Ganti sumber data (opsional)", type=["csv", "xlsx"],
                              help="CSV hasil transformasi, atau XLSX dengan sheet Data_Penjualan.")
try:
    data = baca_unggahan(unggah.getvalue(), unggah.name) if unggah else baca_bawaan()
except Exception as e:  # noqa: BLE001
    st.error(f"Data tidak dapat dibaca: {e}")
    st.stop()

tmin, tmax = data.Tanggal.min().date(), data.Tanggal.max().date()


def reset():
    st.session_state.update(f_outlet=olah.OUTLET, f_kanal=olah.KANAL,
                            f_jenis=olah.JENIS_HARI, f_tgl=(tmin, tmax))


for k, v in dict(f_outlet=olah.OUTLET, f_kanal=olah.KANAL, f_jenis=olah.JENIS_HARI, f_tgl=(tmin, tmax)).items():
    st.session_state.setdefault(k, v)

with st.sidebar:
    f_outlet = st.multiselect("Outlet", olah.OUTLET, key="f_outlet")
    f_kanal = st.multiselect("Kanal penjualan", olah.KANAL, key="f_kanal")
    f_jenis = st.multiselect("Jenis hari", olah.JENIS_HARI, key="f_jenis")
    f_tgl = st.date_input("Rentang tanggal", min_value=tmin, max_value=tmax, key="f_tgl", format="DD/MM/YYYY")
    st.button("Reset filter", on_click=reset, use_container_width=True)
    st.divider()
    st.caption("Data simulasi (fiktif) · 4.380 baris · 1 Jan–31 Des 2025")

if not (isinstance(f_tgl, (tuple, list)) and len(f_tgl) == 2):
    st.info("Pilih tanggal akhir pada filter Rentang tanggal.")
    st.stop()

df = olah.saring(data, f_outlet, f_kanal, f_jenis, f_tgl[0], f_tgl[1])

# ---------------------------------------------------------------- judul
st.markdown('<div class="eyebrow">Fokus audiens: Tim Pemasaran · Visualisasi Data D4</div>', unsafe_allow_html=True)
st.title("Kapan wisatawan mendominasi dan kapan pelanggan lokal menjadi andalan?")
st.markdown(
    f"Penjualan Gudeg Sekar Arum, Yogyakarta, {tmin:%d/%m/%Y}–{tmax:%d/%m/%Y} (data simulasi). "
    "Atur filter di sidebar kiri, lalu baca dari kartu angka ke bawah."
    f'<span class="sw" style="background:{WIS}"></span>Wisatawan'
    f'<span class="sw" style="background:{LOK}"></span>Pelanggan lokal',
    unsafe_allow_html=True,
)

if df.empty:
    st.warning("Tidak ada data untuk kombinasi filter ini. Tekan “Reset filter” atau aktifkan kembali "
               "minimal satu pilihan di tiap kelompok.")
    st.stop()

# ---------------------------------------------------------------- KPI
K, K0 = olah.ringkas(df), olah.ringkas(data)
cols = st.columns(5)
with cols[0]:
    with st.container(border=True):
        st.metric("Omzet bersih", rp(K["omzet"]), help=f"Rp{nf(K['omzet'])}")
with cols[1]:
    with st.container(border=True):
        st.metric("Jumlah transaksi", nf(K["trx"]), help=f"{nf(K['trx'] / K['hari'])} transaksi per hari")
with cols[2]:
    with st.container(border=True):
        st.metric("Rata-rata nilai transaksi", f"Rp{nf(K['avg'])}", help="Omzet bersih ÷ jumlah transaksi")
with cols[3]:
    with st.container(border=True):
        st.metric("Rating berbobot", f"{dec(K['rating'], 2)} / 5" if K["rating"] else "–",
                  help=f"Σ(rating × ulasan) ÷ Σ ulasan; {nf(K['ulasan'])} ulasan")
with cols[4]:
    with st.container(border=True):
        sel = K["pangsa"] - K0["pangsa"]
        st.metric("Pangsa wisatawan", p1(K["pangsa"]),
                  delta=f"{sel:+.1f} poin vs semua data".replace(".", ",") if abs(sel) >= 0.05 else None,
                  delta_color="off", help="Σ transaksi wisatawan ÷ Σ jumlah transaksi")

# ---------------------------------------------------------------- insight otomatis
def teratas(kolom, label_fn=lambda x: x):
    g = olah.agregat(df, kolom).dropna(subset=["pangsa"])
    if len(g) < 2:
        return None
    g = g.sort_values("pangsa", ascending=False)
    return (label_fn(g.index[0]), g.pangsa.iloc[0]), (label_fn(g.index[-1]), g.pangsa.iloc[-1])


baris = []
for kolom, teks in [("Outlet", "Outlet paling bergantung pada wisatawan: <b>{a}</b> ({pa}); paling lokal: <b>{b}</b> ({pb})."),
                    ("Bulan", "Bulan dengan pangsa wisatawan tertinggi: <b>{a}</b> ({pa}); terendah: <b>{b}</b> ({pb})."),
                    ("Kanal_Penjualan", "Kanal paling banyak dipakai wisatawan: <b>{a}</b> ({pa}); paling lokal: <b>{b}</b> ({pb})."),
                    ("Jenis_Hari", "Pangsa wisatawan paling tinggi pada <b>{a}</b> ({pa}) dan paling rendah pada <b>{b}</b> ({pb}).")]:
    r = teratas(kolom, (lambda x: x.lower()) if kolom == "Jenis_Hari" else (lambda x: x))
    if r:
        (a, pa), (b, pb) = r
        baris.append(teks.format(a=a, pa=p1(pa), b=b, pb=p1(pb)))
if not baris:
    baris = ["Filter terlalu sempit untuk membandingkan kelompok. Aktifkan lebih dari satu pilihan."]
st.markdown('<div class="insight"><b>Yang terbaca pada filter ini</b><ul>'
            + "".join(f"<li>{x}</li>" for x in baris) + "</ul></div>", unsafe_allow_html=True)
st.write("")


# ---------------------------------------------------------------- pembantu grafik
def rapikan(fig, tinggi, **kw):
    fig.update_layout(height=tinggi, margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), **kw)
    return fig


def tumpuk_persen(nama, pangsa, wis, lok, total=None, tinggi=300):
    """Batang horizontal 100%: wisatawan vs lokal, dengan label langsung."""
    fig = go.Figure()
    fig.add_bar(y=nama, x=pangsa, orientation="h", name="Wisatawan", marker_color=WIS,
                text=[f"{v:.0f}%" for v in pangsa], textposition="inside", insidetextanchor="middle",
                textfont=dict(color="white"), customdata=[nf(v) for v in wis],
                hovertemplate="Wisatawan: %{x:.1f}% (%{customdata} transaksi)<extra></extra>")
    fig.add_bar(y=nama, x=[100 - v for v in pangsa], orientation="h", name="Pelanggan lokal", marker_color=LOK,
                text=[f"{100 - v:.0f}%" for v in pangsa], textposition="inside", insidetextanchor="middle",
                textfont=dict(color="white"), customdata=[nf(v) for v in lok],
                hovertemplate="Lokal: %{x:.1f}% (%{customdata} transaksi)<extra></extra>")
    fig.update_layout(barmode="stack")
    fig.update_xaxes(range=[0, 100], dtick=25, ticksuffix="%", showgrid=False)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    rapikan(fig, tinggi)
    if total is not None:
        fig.update_layout(margin=dict(l=10, r=70, t=30, b=10))
        for n, t in zip(nama, total):
            fig.add_annotation(x=1, xref="paper", y=n, text=nf(t), showarrow=False, xanchor="left", xshift=8)
    return fig


# ---------------------------------------------------------------- 1. TREN
st.subheader("1 · Tren: kapan wisatawan naik, kapan lokal bertahan")
c1, c2 = st.columns([2, 2])
ukuran = c1.radio("Ukuran", ["Jumlah transaksi", "Pangsa wisatawan (%)", "Omzet bersih"], horizontal=True)
level = c2.radio("Satuan waktu", ["Bulan", "Pekan"], horizontal=True)

if level == "Bulan":
    g = olah.agregat(df, "Bulan_No")
    x = [olah.BULAN_S[m - 1] for m in g.index]
    ttl = "bulan"
else:
    g = olah.agregat(df, "Pekan")
    x = list(g.index)
    ttl = "pekan"

fig = go.Figure()
if ukuran == "Jumlah transaksi":
    st.markdown(f'<div class="sub">Jumlah transaksi per {ttl} pada filter yang dipilih.</div>', unsafe_allow_html=True)
    tampil = len(g) <= 7
    fig.add_bar(x=x, y=g.wis, name="Wisatawan", marker_color=WIS, text=[nf(v) for v in g.wis] if tampil else None,
                textposition="outside", hovertemplate="Wisatawan: %{y:,} transaksi<extra></extra>")
    fig.add_bar(x=x, y=g.lokal, name="Pelanggan lokal", marker_color=LOK,
                text=[nf(v) for v in g.lokal] if tampil else None, textposition="outside",
                hovertemplate="Pelanggan lokal: %{y:,} transaksi<extra></extra>")
    fig.update_layout(barmode="group")
    fig.update_yaxes(title=f"Transaksi per {ttl}", rangemode="tozero")
elif ukuran == "Pangsa wisatawan (%)":
    rata = K["pangsa"]
    st.markdown(f'<div class="sub">Persen transaksi dari wisatawan per {ttl}. Garis putus-putus: rata-rata pada filter ini ({p1(rata)}).</div>',
                unsafe_allow_html=True)
    fig.add_scatter(x=x, y=g.pangsa, mode="lines+markers", name="Pangsa wisatawan",
                    line=dict(color=WIS, width=3), marker=dict(size=8 if level == "Bulan" else 5),
                    hovertemplate="Pangsa wisatawan: %{y:.1f}%<extra></extra>")
    fig.add_scatter(x=x, y=[rata] * len(x), mode="lines", name="Rata-rata",
                    line=dict(color="gray", width=1.5, dash="dash"), hoverinfo="skip")
    fig.update_yaxes(range=[0, 100], dtick=25, ticksuffix="%", title="Persen transaksi dari wisatawan")
else:
    st.markdown(f'<div class="sub">Omzet bersih (gudeg + oleh-oleh − diskon) per {ttl}, dalam juta rupiah.</div>',
                unsafe_allow_html=True)
    fig.add_bar(x=x, y=g.omzet / 1e6, name="Omzet bersih", marker_color="#46515E",
                hovertemplate="Rp%{y:,.1f} juta<extra></extra>")
    fig.update_yaxes(title="Juta rupiah", rangemode="tozero")
    fig.update_layout(showlegend=False)
fig.update_layout(hovermode="x unified")
st.plotly_chart(rapikan(fig, 340), use_container_width=True)

# ---------------------------------------------------------------- 2. PERBANDINGAN
st.subheader("2 · Perbandingan: outlet dan kanal mana yang paling bergantung pada wisatawan")
tab_o, tab_k = st.tabs(["Antar-outlet", "Antar-kanal"])
for tab, kolom in [(tab_o, "Outlet"), (tab_k, "Kanal_Penjualan")]:
    with tab:
        a, b = st.columns(2)
        g = olah.agregat(df, kolom).dropna(subset=["pangsa"]).sort_values("pangsa", ascending=False)
        with a:
            st.markdown('<div class="sub">Komposisi transaksi, diurutkan dari pangsa wisatawan terbesar. Angka di kanan: total transaksi.</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(tumpuk_persen(list(g.index), list(g.pangsa), list(g.wis), list(g.lokal), list(g.trx), 290),
                            use_container_width=True, key=f"cmp_{kolom}")
        with b:
            st.markdown('<div class="sub">Omzet bersih (juta rupiah), diurutkan dari terbesar; label di batang.</div>',
                        unsafe_allow_html=True)
            go_ = g.sort_values("omzet", ascending=False)
            fo = go.Figure(go.Bar(y=list(go_.index), x=go_.omzet / 1e6, orientation="h", marker_color="#46515E",
                                  text=[f"Rp{dec(v / 1e6, 0)} jt" for v in go_.omzet], textposition="inside",
                                  insidetextanchor="end", textfont=dict(color="white"),
                                  hovertemplate="Rp%{x:,.1f} juta<extra></extra>"))
            fo.update_xaxes(title="Juta rupiah", rangemode="tozero")
            fo.update_yaxes(autorange="reversed")
            st.plotly_chart(rapikan(fo, 290, showlegend=False), use_container_width=True, key=f"om_{kolom}")

# ---------------------------------------------------------------- 3. PROPORSI
st.subheader("3 · Proporsi: hari, minggu, dan musim")
a, b = st.columns(2)
J = olah.per_hari(df, "Jenis_Hari").reindex([j for j in olah.JENIS_HARI if j in df.Jenis_Hari.unique()])
with a:
    st.markdown("**Rata-rata transaksi per hari menurut jenis hari**")
    st.markdown('<div class="sub">Σ transaksi ÷ jumlah hari pada jenis itu.</div>', unsafe_allow_html=True)
    lab = [f"{j} ({int(h)} hari)" for j, h in zip(J.index, J.hari)]
    fig = go.Figure()
    fig.add_bar(x=lab, y=J.wis_hari, name="Wisatawan", marker_color=WIS, text=[nf(v) for v in J.wis_hari],
                textposition="outside", hovertemplate="Wisatawan: %{y:.0f} transaksi/hari<extra></extra>")
    fig.add_bar(x=lab, y=J.lokal_hari, name="Pelanggan lokal", marker_color=LOK, text=[nf(v) for v in J.lokal_hari],
                textposition="outside", hovertemplate="Lokal: %{y:.0f} transaksi/hari<extra></extra>")
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="Transaksi per hari", rangemode="tozero")
    st.plotly_chart(rapikan(fig, 320), use_container_width=True)
with b:
    st.markdown("**Komposisi pelanggan menurut jenis hari**")
    st.markdown('<div class="sub">Tiap batang berjumlah 100%.</div>', unsafe_allow_html=True)
    st.plotly_chart(tumpuk_persen(list(J.index), list(J.pangsa), list(J.wis), list(J.lokal), tinggi=320),
                    use_container_width=True)

a, b = st.columns(2)
with a:
    st.markdown("**Pangsa wisatawan menurut hari dalam seminggu**")
    st.markdown('<div class="sub">Berguna untuk menjadwalkan promosi: batang oranye = hari paling “wisatawan”.</div>',
                unsafe_allow_html=True)
    H = olah.agregat(df, "Hari").reindex(olah.HARI).dropna(subset=["pangsa"])
    warna = [WIS if v == H.pangsa.max() else "#C9CED4" for v in H.pangsa]
    fh = go.Figure(go.Bar(x=H.index, y=H.pangsa, marker_color=warna, text=[f"{v:.0f}%" for v in H.pangsa],
                          textposition="outside", hovertemplate="%{x}: %{y:.1f}% wisatawan<extra></extra>"))
    fh.update_yaxes(range=[0, 100], ticksuffix="%", dtick=25, title="Pangsa wisatawan")
    st.plotly_chart(rapikan(fh, 320, showlegend=False), use_container_width=True)
with b:
    st.markdown("**Pangsa wisatawan per outlet dan bulan (heatmap)**")
    st.markdown('<div class="sub">Makin gelap, makin banyak wisatawan. Arahkan kursor untuk angka tepat.</div>',
                unsafe_allow_html=True)
    Hm = olah.agregat(df, ["Outlet", "Bulan_No"]).reset_index()
    bulan_ada = sorted(Hm.Bulan_No.unique())
    outlet_ada = [o for o in olah.OUTLET if o in Hm.Outlet.unique()]
    z, tip = [], []
    for o in outlet_ada:
        zr, tr = [], []
        for m in bulan_ada:
            r = Hm[(Hm.Outlet == o) & (Hm.Bulan_No == m)]
            if len(r) and r.trx.iloc[0] > 0:
                zr.append(r.pangsa.iloc[0])
                tr.append(f"{o}, {olah.BULAN[m - 1]}: {p1(r.pangsa.iloc[0])} ({nf(r.wis.iloc[0])} dari {nf(r.trx.iloc[0])} transaksi)")
            else:
                zr.append(None)
                tr.append(f"{o}, {olah.BULAN[m - 1]}: tidak ada data")
        z.append(zr)
        tip.append(tr)
    fm = go.Figure(go.Heatmap(z=z, x=[olah.BULAN_S[m - 1] for m in bulan_ada], y=outlet_ada, zmin=0, zmax=100,
                              colorscale=[[0, "#FDF0E5"], [1, "#8C3400"]], xgap=2, ygap=2,
                              text=[[("" if v is None else f"{v:.0f}") for v in r] for r in z], texttemplate="%{text}",
                              customdata=tip, hovertemplate="%{customdata}<extra></extra>",
                              colorbar=dict(title="% wis.", ticksuffix="%", len=0.9)))
    fm.update_yaxes(autorange="reversed")
    st.plotly_chart(rapikan(fm, 320), use_container_width=True)

# ---------------------------------------------------------------- data, unduhan, catatan
st.subheader("Data hasil filter dan catatan")
with st.expander("Lihat dan unduh data hasil filter"):
    tampil = df.drop(columns=["Rating_x_Ulasan"]).copy()
    tampil["Tanggal"] = tampil.Tanggal.dt.strftime("%Y-%m-%d")
    tampil["Pekan"] = tampil.Pekan.dt.strftime("%Y-%m-%d")
    st.dataframe(tampil, use_container_width=True, height=300)
    st.download_button("Unduh CSV hasil filter", tampil.to_csv(index=False).encode("utf-8"),
                       file_name="data_hasil_filter.csv", mime="text/csv")
with st.expander("Panduan singkat penggunaan"):
    st.markdown(
        "1. Atur filter di sidebar kiri: outlet, kanal, jenis hari, dan rentang tanggal. Semua angka dan grafik ikut berubah.\n"
        "2. Baca kartu angka di atas, lalu kotak “Yang terbaca pada filter ini”.\n"
        "3. Pada **Tren**, pilih ukuran (transaksi, pangsa wisatawan, omzet) dan satuan waktu (bulan atau pekan).\n"
        "4. Pada **Perbandingan**, pindah antara tab Antar-outlet dan Antar-kanal.\n"
        "5. Pada **Proporsi**, baca komposisi menurut jenis hari, hari dalam seminggu, dan heatmap outlet × bulan.\n"
        "6. Bila muncul “Tidak ada data”, tekan Reset filter."
    )
st.markdown(
    "**Rumus.** Rasio dihitung dari jumlah pembilang dan penyebut, bukan rata-rata rasio harian. "
    "Pangsa wisatawan = Σ Transaksi_Wisatawan ÷ Σ Jumlah_Transaksi. "
    "Rating berbobot = Σ(Rating × Jumlah_Ulasan) ÷ Σ Jumlah_Ulasan. "
    "Omzet bersih = omzet gudeg + omzet oleh-oleh − diskon.\n\n"
    "**Sumber dan batasan.** Data Simulasi Penjualan Gudeg Sekar Arum, Yogyakarta, 2025 (fiktif, hasil simulasi komputer). "
    "Tanggal libur nasional berupa perkiraan. Tidak ada data biaya, sehingga laba dan efektivitas kampanye tidak dapat dihitung. "
    "Korelasi tidak membuktikan sebab-akibat."
)
st.caption("Kelompok A · Visualisasi Data · Universitas Atma Jaya Yogyakarta · Semester Gasal 2026/2027")
