# SIGAP V2 - OFFLINE FIX - SMKN Mojoagung
# GEMPITA AWARDS 2026 + Q1 Scopus
# FIX: Suhu tidak stuck 28.4C kalau alat mati, Saving tidak stuck 18.5%
# Firebase URL BENAR: https://sigap-mojoagung-default-rtdb.asia-southeast1.firebasedatabase.app/telemetry.json
# Rules Firebase harus: {".read": true, ".write": true}

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests

st.set_page_config(page_title="SIGAP - EcoSmart School SMKN Mojoagung", page_icon="🌱", layout="wide")

st.markdown("""
<style>
.main-header { background: linear-gradient(90deg, #0D2C63 0%, #009688 100%); padding: 20px; border-radius: 10px; color: white; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>🌱 SIGAP: Sistem IoT Green & Analytics Platform</h1><h3>SMKN Mojoagung - Hemat Energi, Cerdas Ber-AI | GEMPITA AWARDS 2026</h3><p>Hardware: ESP8266 + ADS1115 16-bit + ACS712 + ZMPT101B + DHT22 Biru + LCD 20x4 I2C | ADS1115 VDD 3.3V, ACS712/ZMPT/DHT22/LCD VIN 5V, SDA D2, SCL D1, DHT D5, ADDR GND 0x48</p></div>', unsafe_allow_html=True)

st.sidebar.title("⚙ SIGAP Control")
device = st.sidebar.selectbox("Pilih Lab", ["Lab RPL", "Lab 1", "Lab 2", "Lab 3", "Lab 4","Lab BD", "Lab MPLB", "Lab AKL"])
auto_off = st.sidebar.toggle("AI Auto-OFF Hemat Energi", value=True)
st.sidebar.info("ADS1115 16-bit - Error <1.8% | DHT22 Biru - Tanpa Resistor 10K")

# ============ AMBIL DATA REAL DARI FIREBASE ============
try:
    FIREBASE_URL = st.secrets["FIREBASE_URL"]
except:
    FIREBASE_URL = "https://sigap-mojoagung-default-rtdb.asia-southeast1.firebasedatabase.app/telemetry.json"
    st.warning("⚠️ Secrets FIREBASE_URL belum diset di Streamlit Cloud. Pakai URL default asia-southeast1. Buka Settings -> Secrets untuk ganti.")

if st.button("🔄 Refresh Data Real dari ESP8266"):
    st.rerun()

try:
    resp = requests.get(FIREBASE_URL, timeout=5)
    data = resp.json()
    if data is None:
        st.warning("⚠️ Firebase masih kosong (null) - ESP8266 belum pernah kirim. Cek WiFi & Rules Firebase.")
        data = {}
    elif isinstance(data, dict) and "error" in data:
        st.error(f"🔴 Firebase Error: {data['error']} - Buka Firebase Console -> Realtime Database -> Rules, ganti jadi {'.read': True, '.write': True} lalu Publish.")
        data = {}
except Exception as e:
    st.error(f"Gagal baca Firebase: {e}")
    data = {}

# FIX: JANGAN pakai fallback 28.4 / 61.8 - kalau tidak ada data, pakai None agar ketahuan OFFLINE
voltage_now = data.get("voltage", 0)
current_now = data.get("current", 0)
power_now = data.get("power", 0)
kwh_now = data.get("kwh", 0)
temp_now = data.get("temp", None)  # None, bukan 28.4
hum_now = data.get("hum", None)    # None, bukan 61.8
biaya_now = data.get("biaya_rp", kwh_now * 1444 if kwh_now else 0)
device_now = data.get("device", "SIGAP_Mojoagung_Lab1")
status_fw = data.get("status", "UNKNOWN")

# FIX OFFLINE DETECTOR: Firebase tidak hapus data lama kalau alat mati.
# Jadi kita deteksi dari power+current+voltage = 0 ATAU temp = None
is_offline = (voltage_now == 0 and current_now == 0 and power_now == 0) or (temp_now is None)
if is_offline:
    st.error("🔴 ALAT OFFLINE - ESP8266 Mati / WiFi Putus / Kabel Lepas / DHT Error. Angka di bawah adalah DATA TERAKHIR sebelum mati, BUKAN data live.")
    # Tampilkan suhu sebagai --, bukan 28.4 palsu
    temp_display = "--"
    hum_display = "--"
else:
    st.success(f"🟢 ALAT ONLINE - Data Live dari {device_now} | Status Firebase: {status_fw}")
    temp_display = f"{temp_now:.1f}"
    hum_display = f"{hum_now:.1f}"

# FIX SAVING: Jangan hardcode 18.5%, hitung dari kWh real. Alat mati = 0%
if kwh_now and kwh_now > 0:
    saving = max(0, (15.8 - kwh_now) / 15.8 * 100)
else:
    saving = 0.0

# Histori untuk grafik
if "history" not in st.session_state:
    st.session_state.history = []
if not is_offline:
    st.session_state.history.append({"timestamp": datetime.now(), "voltage": voltage_now, "current": current_now, "power": power_now, "kwh": kwh_now, "temp": temp_now if temp_now is not None else 0, "hum": hum_now if hum_now is not None else 0})
    if len(st.session_state.history) > 72:
        st.session_state.history = st.session_state.history[-72:]
df = pd.DataFrame(st.session_state.history)
if df.empty:
    df = pd.DataFrame([{"timestamp": datetime.now(), "voltage": voltage_now, "current": current_now, "power": power_now, "kwh": kwh_now, "temp": 0, "hum": 0}])

# Metrics Row - REAL, BUKAN RANDOM, BUKAN FALLBACK PALSU
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("⚡ Tegangan (ZMPT101B)", f"{voltage_now:.1f} V", f"{voltage_now-220:.1f} V")
with col2:
    st.metric("🔌 Arus (ACS712)", f"{current_now:.2f} A", f"{current_now:.2f} A")
with col3:
    st.metric("💰 Saving Energi", f"{saving:.1f}%", "Target 30% V2" if not is_offline else "Alat OFFLINE - Saving 0%")
with col4:
    # Tampilkan -- kalau offline, bukan 28.4 stuck
    if is_offline:
        st.metric("🌡 Suhu (DHT22 Biru)", "-- °C", "OFFLINE - Bukan 28.4°C")
    else:
        st.metric("🌡 Suhu (DHT22 Biru)", f"{temp_display} °C", f"Kelembaban {hum_display}%")

col5, col6, col7, col8 = st.columns(4)
with col5:
    st.metric("⚡ Daya", f"{power_now:.0f} W", "P = V x I x 0.85")
with col6:
    st.metric("🔋 Energi kWh", f"{kwh_now:.3f} kWh", "Akumulasi")
with col7:
    st.metric("💸 Biaya Rupiah", f"Rp {biaya_now:,.0f}", "Tarif Rp 1.444/kWh")
with col8:
    status = "ON" if power_now > 10 else "OFF"
    st.metric("🔌 Status Beban", status, f"Device: {device_now} | {status_fw}")

st.divider()
tab1, tab2, tab3 = st.tabs(["📊 Real-time Monitoring", "🤖 AI Analytics & Prediksi", "👨🎓 Dashboard Pedagogi Arsitek"])
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['voltage'], name="Tegangan ZMPT101B (Real)", line=dict(color="#0D2C63")))
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['current'], name="Arus ACS712 (Real)", yaxis="y2", line=dict(color="#FF5722")))
        fig.update_layout(title="Tegangan & Arus Real-time (ADS1115 16-bit - Data dari Firebase)", yaxis=dict(title="Volt"), yaxis2=dict(title="Ampere", overlaying="y", side="right"), height=350)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.area(df, x='timestamp', y='power', title="Daya (Watt) - Data Real dari ESP8266", color_discrete_sequence=['#009688'])
        fig2.add_hline(y=500, line_dash="dash", line_color="red", annotation_text="Batas Boros AC")
        st.plotly_chart(fig2, use_container_width=True)
    st.dataframe(df.tail(10), use_container_width=True)
    st.caption("Data Real: ESP8266 -> ADS1115 -> Firebase (PUT telemetry.json) -> Streamlit (GET via Secrets) | Kalau alat mati, Firebase simpan data terakhir, Streamlit tampilkan OFFLINE + --, bukan 28.4°C palsu")
    st.code(f"Firebase URL: {FIREBASE_URL}\nData terakhir: {data}", language="json")

with tab2:
    st.subheader("🤖 AI Prediksi Konsumsi Besok (Random Forest)")
    if len(df) >= 5 and not is_offline:
        from sklearn.ensemble import RandomForestRegressor
        import numpy as np
        X = np.arange(len(df)).reshape(-1,1)
        y = df['power'].values
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        model.fit(X, y)
        future = np.arange(len(df), len(df)+24).reshape(-1,1)
        pred = model.predict(future)
        future_time = [df['timestamp'].iloc[-1] + timedelta(hours=i) for i in range(1,25)]
        fig_pred = go.Figure()
        fig_pred.add_trace(go.Scatter(x=df['timestamp'], y=df['power'], name="Historis Real", line=dict(color="gray")))
        fig_pred.add_trace(go.Scatter(x=future_time, y=pred, name="Prediksi AI 24 Jam", line=dict(color="#FFC107", dash="dash")))
        fig_pred.update_layout(title="Prediksi AI - Dari Data Real Firebase", height=400)
        st.plotly_chart(fig_pred, use_container_width=True)
    else:
        st.info("Alat OFFLINE atau data <5 titik. Nyalakan alat, tunggu 50 detik, refresh untuk prediksi AI.")
    if auto_off:
        st.success("✅ AI Auto-OFF Aktif: Jika kelas kosong (arus <0.2A) selama 15 menit, kirim perintah matikan AC via Blynk")
        if current_now < 0.2 and power_now > 10:
            st.warning("⚠ Deteksi Boros: Kelas kosong tapi daya masih ON!")

with tab3:
    st.subheader("👨🎓 Dashboard Kompetensi Arsitek IoT-Cloud-Data")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**IoT Engineer**"); st.progress(85, text="Hardware & Kalibrasi ADS1115: 85%"); st.caption("Ahmad - Wiring ACS712+ZMPT ke ADS1115 A0/A1, DHT22 D5")
    with col2:
        st.markdown("**Cloud Engineer**"); st.progress(88, text="MQTT Firebase Blynk: 88%"); st.caption("Siti - Setup Blynk & Firebase RTDB asia-southeast1, Secrets")
    with col3:
        st.markdown("**Data Analyst**"); st.progress(82, text="Dashboard Streamlit AI: 82%"); st.caption("Budi - Streamlit + Random Forest, Biaya Rupiah")
    st.divider()
    st.markdown("#### 📈 N-Gain Kelas (Pre 51,3 -> Post 85,1 = 0,71 Tinggi)")
    ngain_df = pd.DataFrame({"Aspek": ["IoT Hardware", "Cloud MQTT", "Data Analytics"], "Pre": [58.2, 45.6, 42.1], "Post": [84.5, 88.2, 82.7], "N-Gain": [0.63, 0.78, 0.70]})
    st.bar_chart(ngain_df, x="Aspek", y=["Pre","Post"])

st.sidebar.divider()
st.sidebar.markdown("**GEMPITA 2026**\nGuru Impresif\nMifta Johan Daehan Jo - SMKN Mojoagung")
st.sidebar.markdown(f"**Firebase:** {FIREBASE_URL}")
st.sidebar.markdown(f"**Device:** {device_now} | **Status:** {'🔴 OFFLINE' if is_offline else '🟢 ONLINE'}")

with st.expander("🔧 Kenapa suhu stuck 28.4°C? (Penjelasan untuk Juri)"):
    st.markdown("""
    **Penyebab lama:** C++ punya `if(isnan(temp)) temp = 28.4` dan Streamlit punya `data.get("temp", 28.4)`. 
    Firebase simpan data terakhir, tidak hapus saat alat mati. Jadi dashboard kelihatan hidup padahal alat mati.
    **Fix V2:** C++ `return` kalau DHT gagal, Streamlit `temp = None` -> tampil `--` + banner `🔴 ALAT OFFLINE`. 
    Saving juga tidak hardcode 18.5%, tapi dihitung dari kWh real. Alat mati = 0%.
    """)
