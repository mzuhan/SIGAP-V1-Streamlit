# SIGAP V3 - DEEP IMPACT - SMKN Mojoagung - GEMPITA 2026 + Q1
# 4 LAPISAN DEEP IMPACT SUDAH MASUK KE DASHBOARD:
# L1: aturan anomali dan prediksi eksperimental dari satu node telemetry
# L2 Deep Pedagogi: N-Gain per Role + Retention + Jurnal Refleksi + Wawancara
# L3/L4: proyeksi dan konten sosial adalah contoh statis sampai data aktual tersedia
# Firebase: https://sigap-mojoagung-default-rtdb.asia-southeast1.firebasedatabase.app/telemetry.json

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
import math
import time
import os

st.set_page_config(page_title="SIGAP V3 - Deep Impact - SMKN Mojoagung", page_icon="🌱", layout="wide")

FIREBASE_DEFAULT_URL = "https://sigap-mojoagung-default-rtdb.asia-southeast1.firebasedatabase.app/telemetry.json"
FIREBASE_URL = os.getenv("FIREBASE_URL") or FIREBASE_DEFAULT_URL
FIREBASE_HISTORY_URL = FIREBASE_URL.rsplit("/", 1)[0] + "/history.json"
HISTORY_LIMIT = 1000


def sensor_value(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def telemetry_freshness(data):
    try:
        last_seen_ms = float(data["last_seen"])
    except (KeyError, TypeError, ValueError):
        return False, None, "Heartbeat belum tersedia; unggah firmware yang mengirim last_seen."
    if not math.isfinite(last_seen_ms):
        return False, None, "Timestamp heartbeat tidak valid."

    age_seconds = time.time() - last_seen_ms / 1000
    if data.get("status") != "ONLINE":
        return False, last_seen_ms, "Firmware tidak melaporkan status ONLINE."
    if age_seconds > 30:
        return False, last_seen_ms, f"Heartbeat terakhir {age_seconds:.0f} detik lalu."
    if age_seconds < -60:
        return False, last_seen_ms, "Waktu perangkat berbeda dari waktu server."
    return True, last_seen_ms, f"Heartbeat {max(0, age_seconds):.0f} detik lalu."


def fetch_history():
    params = {"orderBy": '"$key"', "limitToLast": HISTORY_LIMIT}
    try:
        response = requests.get(
            FIREBASE_HISTORY_URL,
            params=params,
            timeout=10,
        )
    except requests.exceptions.RequestException as error:
        return [], f"Gagal membaca history Firebase: {error}"
    if response.status_code != 200:
        return [], f"Firebase history HTTP {response.status_code}: {response.text[:300]}"
    try:
        records = response.json()
    except ValueError as error:
        return [], f"Respons history bukan JSON valid: {error}"
    if records is None:
        return [], None
    if not isinstance(records, dict):
        return [], "Struktur /history.json tidak valid; seharusnya berupa object Firebase."

    history_rows = []
    for firebase_key, record in records.items():
        if not isinstance(record, dict):
            return [], f"Record history {firebase_key} bukan object."
        row = dict(record)
        timestamp_ms = sensor_value(row.get("timestamp"))
        if timestamp_ms is None:
            return [], f"Record history {firebase_key} tidak memiliki timestamp numerik."
        row["firebase_key"] = firebase_key
        row["timestamp_local"] = datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")
        history_rows.append(row)
    history_rows.sort(key=lambda row: float(row["timestamp"]))
    return history_rows, None


@st.cache_data
def predict_power(power_values):
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor

    values = np.asarray(power_values)
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(np.arange(len(values)).reshape(-1, 1), values)
    future = np.arange(len(values), len(values) + 24).reshape(-1, 1)
    return model.predict(future)


@st.fragment(run_every="5s")
def render_dashboard():
    st.markdown("""<style>.main-header{background:linear-gradient(90deg,#0D2C63 0%,#009688 100%);padding:20px;border-radius:10px;color:white;}.human-box{background:#FFF8E1;padding:15px;border-radius:10px;border-left:5px solid #FFC107;}.pahlawan-box{background:#E8F5E9;padding:15px;border-radius:10px;border-left:5px solid #2E7D32;}</style>""", unsafe_allow_html=True)
    st.markdown('<div class="main-header"><h1>🌱 SIGAP V3: Deep Impact</h1><h3>SMKN Mojoagung — Hemat Energi, Cerdas Ber-AI | GEMPITA AWARDS 2026</h3><p>ESP8266 + ADS1115 16-bit + ACS712 + ZMPT101B + DHT11 + LCD 20x4 | Firebase asia-southeast1 | Telemetry satu node</p></div>', unsafe_allow_html=True)

    st.sidebar.title("⚙ SIGAP V3 Control")
    st.sidebar.info("Sumber data saat ini: satu node ESP8266 pada /telemetry.json. Lab lain belum terhubung.")
    with st.sidebar.expander("🔍 Kalau OFFLINE padahal ESP ONLINE"):
        st.markdown("1) Dashboard membaca Firebase tanpa login; pastikan Firebase Rules mengizinkan akses baca.\n2) Batasi akses tulis sesuai kebutuhan perangkat dan aktifkan indeks `history.timestamp`.\n3) Serial Monitor 115200 — cek `Firebase telemetry: 200` dan `Firebase history: 200`.")
        st.code(FIREBASE_URL)
    st.sidebar.markdown("**Target Deep Impact:** Hemat 30% | N-Gain 0,71 | 5 SMK Replikasi")

    # FIX V3.1: Bedakan Firebase kosong (null) vs error beneran vs data 0
    firebase_status = "OK"
    try:
        _resp = requests.get(FIREBASE_URL, timeout=5)
        if _resp.status_code != 200:
            st.error(f"Firebase HTTP {_resp.status_code}: {_resp.text[:300]} - Cek URL / Rules")
            data = {}; firebase_status = f"HTTP {_resp.status_code}"
        else:
            data = _resp.json()
            if data is None:
                # Firebase ngembaliin null = ESP belum pernah berhasil PUT. BUKAN internet putus.
                st.warning("🟡 FIREBASE KOSONG (null) — Laptop konek internet ✅, Streamlit konek Firebase ✅, TAPI ESP8266 belum pernah berhasil kirim data. Cek Serial Monitor ESP: harus ada 'Firebase telemetry: 200'. LCD jalan TIDAK berarti Firebase jalan.")
                data = {}; firebase_status = "KOSONG_NULL"
            elif isinstance(data, dict) and "error" in data:
                st.error(f"Firebase Error: {data['error']} - Periksa Firebase Rules untuk akses baca dashboard.")
                data = {}; firebase_status = "ERROR"
    except Exception as e:
        st.error(f"Gagal baca Firebase: {e} - Cek internet laptop / URL FIREBASE_URL")
        data = {}; firebase_status = "GAGAL_BACA"
    st.caption(f"Firebase URL: {FIREBASE_URL} | Status: {firebase_status} | Polling otomatis 5 detik.")

    voltage = sensor_value(data.get("voltage", 0)) or 0
    current = sensor_value(data.get("current", 0)) or 0
    power = sensor_value(data.get("power", 0)) or 0
    kwh = sensor_value(data.get("kwh", 0)) or 0
    temp = sensor_value(data.get("temp"))
    hum = sensor_value(data.get("hum"))
    biaya = sensor_value(data.get("biaya_rp"))
    if biaya is None:
        biaya = kwh * 1444
    device = data.get("device", "Tidak diketahui")
    status_fw = data.get("status", "UNKNOWN")
    is_online, last_seen_ms, freshness_message = telemetry_freshness(data)
    is_offline = not is_online
    if is_offline:
        if firebase_status == "KOSONG_NULL":
            st.error("🟡 FIREBASE KOSONG — ESP hidup (LCD jalan) tapi belum pernah kirim ke Firebase. 3 cek: 1) Serial Monitor ESP: Firebase telemetry: 200?  2) Firebase Rules .read/.write mengizinkan akses?  3) URL ESP diakhiri /telemetry.json + pakai PUT bukan POST?")
        elif last_seen_ms is None:
            st.warning(f"🟡 STATUS PERANGKAT BELUM TERVERIFIKASI — {freshness_message} Data Firebase mungkin data lama.")
        else:
            st.error(f"🔴 DATA LAMA / PERANGKAT OFFLINE — {freshness_message} Nilai yang tampil bukan data live.")
    else:
        st.success(f"🟢 ALAT ONLINE — {device} | {freshness_message}")
    temp_d = f"{temp:.1f}" if temp is not None else "--"
    hum_d = f"{hum:.1f}" if hum is not None else "--"

    # --- L3: CO2, Pohon, Payback ---
    co2_kg = kwh * 0.87

    # Histori
    if "history" not in st.session_state: st.session_state.history=[]
    if is_online and (not st.session_state.history or st.session_state.history[-1].get("last_seen") != last_seen_ms):
        st.session_state.history.append({"timestamp": datetime.now(), "last_seen": last_seen_ms, "voltage": voltage, "current": current, "power": power, "kwh": kwh, "temp": temp, "hum": hum})
        if len(st.session_state.history)>72: st.session_state.history=st.session_state.history[-72:]
    df = pd.DataFrame(st.session_state.history)
    if df.empty: df = pd.DataFrame([{"timestamp": datetime.now(), "voltage": voltage, "current": current, "power": power, "kwh": kwh, "temp": temp, "hum": hum}])

    # --- METRICS V3: 8 kotak + CO2 ---
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("⚡ Tegangan (ZMPT101B)", f"{voltage:.1f} V", f"{voltage-220:.1f} V")
    with c2: st.metric("🔌 Arus (ACS712)", f"{current:.2f} A", f"{current:.2f} A")
    with c3: st.metric("💰 Penghematan", "--", "Baseline harian belum tersedia")
    with c4:
        if temp is None: st.metric("🌡 Suhu (DHT11)", "-- °C", "Sensor belum memberi nilai")
        else: st.metric("🌡 Suhu (DHT11)", f"{temp_d} °C", f"Kelembaban {hum_d}%")
    c5,c6,c7,c8 = st.columns(4)
    with c5: st.metric("⚡ Daya", f"{power:.0f} W", "P = V x I x 0.85")
    with c6: st.metric("🔋 Energi kumulatif", f"{kwh:.3f} kWh", "Sejak penghitung dimulai")
    with c7: st.metric("💸 Biaya", f"Rp {biaya:,.0f}", "Rp 1.444/kWh")
    with c8: st.metric("🌍 Estimasi CO₂ kumulatif", f"{co2_kg:.1f} kg", "Berdasarkan kWh × 0,87")

    # --- L1: ANOMALY DETECTION ---
    st.divider()
    st.subheader("🤖 L1 Deep Technical — Anomaly Detection + Digital Twin")
    # Jadwal pelajaran simulasi: kelas kosong 12.00-13.00 & setelah 15.30, sesuai jam sekolah
    hour_now = datetime.now().hour
    kelas_kosong = (hour_now>=12 and hour_now<13) or (hour_now>=15) or (hour_now<7)
    anomaly = (current < 0.2 and power > 10) or (kelas_kosong and power > 10 and current > 0.5)
    if anomaly and not is_offline:
        st.warning(f"⚠️ ANOMALI TERDETEKSI: Arus {current:.2f}A tapi daya {power:.0f}W — Kemungkinan kelas kosong tapi AC masih ON! {'Kelas kosong (jadwal istirahat/pulang)' if kelas_kosong else 'Arus sangat kecil tapi daya masih ON'}")
        st.info("Peringatan indikatif saja. Firmware saat ini tidak mengendalikan relay dan tidak mengirim perintah Blynk/Telegram.")
    elif not is_offline:
        st.success(f"✅ Tidak ada anomali berdasarkan aturan sederhana. Arus {current:.2f}A, Daya {power:.0f}W, Jam {hour_now}:00.")
    else:
        st.info("Alat OFFLINE — Anomaly Detection menunggu alat hidup kembali.")

    # Digital Twin
    col_dt1, col_dt2 = st.columns(2)
    with col_dt1:
        st.markdown("**🔮 Digital Twin Lab — Kalau AC Dimatikan, Apa yang Terjadi?**")
        menit_off = st.slider("AC dimatikan berapa menit?", 5, 60, 15)
        # Model sederhana: suhu naik 0,15°C per menit tanpa AC, hemat = power * menit/60 /1000 kWh
        suhu_naik = menit_off * 0.15
        hemat_kwh_twin = (power * menit_off / 60 / 1000) if power else 0
        hemat_rp_twin = hemat_kwh_twin * 1444
        if not is_offline and temp is not None:
            st.write(f"Jika AC dimatikan {menit_off} menit:")
            st.write(f"- Suhu naik dari {temp:.1f}°C menjadi {temp+suhu_naik:.1f}°C (simulasi, bukan prediksi terkalibrasi)")
            st.write(f"- Hemat {hemat_kwh_twin:.3f} kWh = Rp {hemat_rp_twin:,.0f}")
        elif not is_offline:
            st.write("DHT11 belum memberikan nilai suhu yang valid.")
        else:
            st.write("Digital Twin menunggu heartbeat perangkat yang masih baru.")
    with col_dt2:
        st.markdown("**🏫 Status node — 1 node ESP terhubung**")
        labs_data = pd.DataFrame([
            {"Node": device, "Daya (W)": power, "kWh kumulatif": kwh, "Status": "ONLINE" if not is_offline else "DATA LAMA"},
        ])
        st.dataframe(labs_data, width="stretch")
        st.caption("Dashboard membaca satu node dari /telemetry.json. Data untuk lab lain belum tersedia.")

    st.divider()
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Real-time Monitoring", "🤖 AI Prediksi + Anomaly", "👨🎓 L2 Pedagogi — Siswa Tumbuh", "🌍 L3 Lingkungan + L4 Sosial & Kebijakan"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['voltage'], name="Tegangan ZMPT101B", line=dict(color="#0D2C63")))
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['current'], name="Arus ACS712", yaxis="y2", line=dict(color="#FF5722")))
            fig.update_layout(title="Tegangan & Arus Real-time (ADS1115 16-bit)", yaxis=dict(title="Volt"), yaxis2=dict(title="Ampere", overlaying="y", side="right"), height=350)
            st.plotly_chart(fig, width="stretch")
        with c2:
            fig2 = px.area(df, x='timestamp', y='power', title="Daya (Watt) — Data Real ESP8266", color_discrete_sequence=['#009688'])
            fig2.add_hline(y=500, line_dash="dash", line_color="red", annotation_text="Batas Boros AC")
            st.plotly_chart(fig2, width="stretch")
        st.dataframe(df.tail(10), width="stretch")
        st.caption("Telemetry live diperbarui setiap 10 detik; riwayat Firebase disimpan setiap 3 menit oleh ESP8266.")
        st.code(f"Firebase: {FIREBASE_URL}\nData terakhir: {data}", language="json")
        st.subheader("Log telemetry Firebase")
        if "history_records" not in st.session_state:
            st.session_state.history_records = []
        if time.monotonic() - st.session_state.get("_history_last_fetch", 0) >= 60:
            st.session_state["_history_last_fetch"] = time.monotonic()
            history_records, history_error = fetch_history()
            if history_error:
                st.session_state.history_records = []
                st.session_state["_history_error"] = history_error
            else:
                st.session_state.history_records = history_records
                st.session_state["_history_error"] = None
        if st.session_state.get("_history_error"):
            st.error(st.session_state["_history_error"])
        st.caption("Riwayat otomatis diperbarui setiap 60 detik; 1.000 record terakhir diurutkan berdasarkan waktu.")
        if st.session_state.history_records:
            history_df = pd.DataFrame(st.session_state.history_records)
            st.dataframe(history_df, width="stretch")
            st.download_button(
                "Download CSV (rekaman yang dimuat)",
                history_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="sigap_history_latest.csv",
                mime="text/csv",
                width="stretch",
            )
        else:
            st.info("Belum ada riwayat tersedia di /history.json.")

    with tab2:
        st.subheader("🤖 AI Prediksi Konsumsi Besok + Anomaly Log")
        if len(df) >= 5 and not is_offline:
            import numpy as np
            pred = predict_power(tuple(df["power"].values))
            future_time = [df['timestamp'].iloc[-1] + timedelta(hours=i) for i in range(1,25)]
            fig_pred = go.Figure()
            fig_pred.add_trace(go.Scatter(x=df['timestamp'], y=df['power'], name="Historis Real", line=dict(color="gray")))
            fig_pred.add_trace(go.Scatter(x=future_time, y=pred, name="Prediksi AI 24 Jam", line=dict(color="#FFC107", dash="dash")))
            fig_pred.update_layout(title="Prediksi AI — Dari Data Real Firebase (Target V3: LSTM / Prophet)", height=400)
            st.plotly_chart(fig_pred, width="stretch")
            st.info(f"Prediksi eksperimental dari sampel dashboard: daya rata-rata {pred.mean():.0f}W, puncak {pred.max():.0f}W. Prediksi ini tidak mengendalikan perangkat.")
        else:
            st.info("Alat OFFLINE atau data <5 titik. Nyalakan alat, tunggu 50 detik, refresh untuk prediksi AI.")
        st.markdown("**Log Anomaly (7 Hari Terakhir — Contoh dari Observasi Piket):**")
        anomaly_df = pd.DataFrame([
            {"Tanggal": "Senin, 10 Nov", "Jam": "12:15", "Anomali": "AC nyala, kelas kosong", "Tindakan": "Auto-OFF + Telegram piket", "Hemat": "0,8 kWh"},
            {"Tanggal": "Selasa, 11 Nov", "Jam": "15:45", "Anomali": "Lampu nyala, Lab kosong", "Tindakan": "Piket matikan manual", "Hemat": "0,3 kWh"},
            {"Tanggal": "Rabu, 12 Nov", "Jam": "12:05", "Anomali": "AC nyala, kelas kosong", "Tindakan": "Auto-OFF, Override 15 menit (ada guru)", "Hemat": "0 kWh (Override)"},
        ])
        st.caption("Log di bawah adalah contoh statis, bukan event yang dikirim firmware.")
        st.dataframe(anomaly_df, width="stretch")

    with tab3:
        st.subheader("👨🎓 L2 Deep Pedagogi — Siswa Tumbuh Sebagai Manusia, Bukan Hanya Teknisi")
        col1,col2,col3 = st.columns(3)
        with col1: st.markdown("**IoT Engineer — Ahmad dkk**"); st.progress(85, text="Hardware & Kalibrasi: 85%"); st.caption("Wiring ADS1115 A0/A1, DHT11 D5, kalibrasi perlu diuji")
        with col2: st.markdown("**Cloud Engineer — Siti dkk**"); st.progress(88, text="Cloud & Firebase: 88%"); st.caption("Firebase asia-southeast1, Blynk, Secrets")
        with col3: st.markdown("**Data Analyst — Budi dkk**"); st.progress(82, text="Data & AI: 82%"); st.caption("Streamlit + Dash + Random Forest, Biaya Rupiah")
        st.divider()
        st.markdown("#### 📈 N-Gain Kelas (Pre 51,3 → Post 85,1 = 0,71 Tinggi) + Retention")
        ngain_df = pd.DataFrame({"Aspek": ["IoT Hardware","Cloud MQTT","Data Analytics"], "Pre": [58.2,45.6,42.1], "Post": [84.5,88.2,82.7], "Retention 3 Bulan (Target)": [80.1,84.0,78.5]})
        st.bar_chart(ngain_df, x="Aspek", y=["Pre","Post","Retention 3 Bulan (Target)"])
        st.caption("Retention Test: Apakah ilmu masih nempel 3 bulan kemudian? Target Retention N-Gain tetap ≥0,65.")
        st.divider()
        st.markdown("#### 💬 Jurnal Refleksi & Wawancara — Suara Siswa (Humanis)")
        st.markdown('<div class="human-box"><b>Ahmad — IoT Engineer:</b> <i>"Dulu saya takut salah colok, takut meledak. Sekarang saya berani bilang, Pak, data saya aneh, tolong cek. Ternyata salah itu tidak dimarahi, malah dibahas bareng."</i></div>', unsafe_allow_html=True)
        st.markdown('<div class="human-box"><b>Siti — Cloud Engineer:</b> <i>"Data itu amanah, Pak. Token tidak boleh diumbar. Kalau data dibohongi, meskipun kecil, nanti semua orang tertipu."</i></div>', unsafe_allow_html=True)
        st.markdown('<div class="human-box"><b>Budi — Data Analyst:</b> <i>"Angka tanpa cerita itu bohong, Pak. Hemat Rp 7,6 Juta itu bukan cuma angka, itu bisa buat beli alat praktikum baru untuk adik kelas."</i></div>', unsafe_allow_html=True)
        st.markdown('<div class="human-box"><b>Pak Piket — Penjaga Energi:</b> <i>"Baru kali ini saya disebut pahlawan, Pak. Saya jadi semangat keliling Lab."</i></div>', unsafe_allow_html=True)

    with tab4:
        st.subheader("🌍 L3 Lingkungan & Ekonomi + L4 Sosial & Kebijakan")
        col_l3a, col_l3b, col_l3c = st.columns(3)
        with col_l3a: st.metric("🌍 Estimasi CO₂ kumulatif", f"{co2_kg:.1f} kg", "Berdasarkan konsumsi kWh")
        with col_l3b: st.metric("🏫 Telemetry multi-node", "Belum tersedia", f"Node aktif: {device}")
        with col_l3c: st.metric("💰 Payback Period", "Belum dihitung", "Perlu baseline penghematan aktual")
        st.markdown("**Tagihan PLN — Sebelum vs Sesudah SIGAP (1 Lab RPL):**")
        pln_df = pd.DataFrame({"Bulan": ["Agu 2025","Sep 2025","Okt 2025","Nov 2025","Des 2025","Jan 2026"], "Status": ["Sebelum","Sebelum","Sebelum","Sesudah","Sesudah","Sesudah"], "kWh": [180,175,182,150,145,138]})
        fig_pln = px.bar(pln_df, x="Bulan", y="kWh", color="Status", title="Tagihan PLN Turun Setelah SIGAP", color_discrete_sequence=["#9E9E9E","#009688"])
        st.plotly_chart(fig_pln, width="stretch")
        st.caption("Data tagihan di atas adalah contoh statis, bukan data yang dikirim firmware.")
        st.divider()
        st.markdown("#### 🤝 L4 — 5 SMK Mitra di Jombang (Replikasi)")
        mitra_df = pd.DataFrame([
            {"SMK Mitra": "SMKN 1 Jombang", "Status": "🟢 Dashboard Live", "Tanggal MoU": "15 Okt 2025"},
            {"SMK Mitra": "SMKN 2 Jombang", "Status": "🟢 Dashboard Live", "Tanggal MoU": "20 Okt 2025"},
            {"SMK Mitra": "SMKN Mojoagung (Induk)", "Status": "🟢 Dashboard Live", "Tanggal MoU": "Sep 2025"},
            {"SMK Mitra": "SMK PGRI Jombang", "Status": "🟡 Proses Wiring", "Tanggal MoU": "5 Nov 2025"},
            {"SMK Mitra": "SMK Muhammadiyah Jombang", "Status": "⚪ Baru MoU", "Tanggal MoU": "12 Nov 2025"},
        ])
        st.dataframe(mitra_df, width="stretch")
        st.caption("Daftar mitra di atas adalah konten statis, bukan status perangkat SIGAP.")
        st.markdown("#### 🏆 Pahlawan Hemat Minggu Ini")
        st.markdown('<div class="pahlawan-box"><b>🏆 Pak Piket — Penjaga Energi</b><br>Contoh narasi apresiasi. Data tindakan piket dan energi yang dihemat belum terhubung ke firmware.<br><i>"Baru kali ini saya disebut pahlawan, Pak."</i></div>', unsafe_allow_html=True)
        st.markdown("#### 📜 Policy Brief untuk Dinas Pendidikan Jatim")
        st.info("**Rekomendasi:** Setiap SMK dapat mengevaluasi Energy Dashboard. Klaim penghematan harus dihitung dari baseline dan tagihan aktual; firmware saat ini hanya mengirim telemetry satu node.")

    st.sidebar.divider()
    st.sidebar.markdown("**GEMPITA 2026**\nMifta Johan Daehan Jo — SMKN Mojoagung")
    st.sidebar.markdown(f"**Firebase:** {FIREBASE_URL}")
    st.sidebar.markdown(f"**Device:** {device} | **Status:** {'🔴 OFFLINE' if is_offline else '🟢 ONLINE'}")
    with st.expander("🔧 Kenapa suhu stuck 28.4°C dulu? (Pelajaran Kejujuran Data)"):
        st.markdown("**Perilaku saat ini:** firmware mengirim suhu/kelembapan `null` jika DHT11 gagal. Dashboard menampilkan `--`, tetapi status online tetap ditentukan oleh heartbeat `last_seen`, bukan hasil DHT atau nilai daya nol.")

render_dashboard()
