import streamlit as st
import os
import datetime
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO

# ─── Sayfa Ayarları ───
st.set_page_config(
    page_title="Eskrim Kılıç - Reaksiyon Kronometresi",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── CSS ───
css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─── Session State ───
if "athlete_name" not in st.session_state:
    st.session_state.athlete_name = ""
if "results" not in st.session_state:
    st.session_state.results = []

# ─── Sidebar ───
with st.sidebar:
    st.markdown("### 🤺 Sporcu")
    name = st.text_input("Ad Soyad", value=st.session_state.athlete_name)
    if name:
        st.session_state.athlete_name = name
    
    st.markdown("### 🎤 Ses Hassasiyeti")
    threshold = st.slider("Eşik", 0.01, 0.50, 0.08, 0.01, 
                          help="Düşük = daha hassas, Yüksek = daha az hassas")
    
    st.divider()
    if st.session_state.results:
        if st.button("🗑️ Sonuçları Temizle", use_container_width=True):
            st.session_state.results = []
            st.rerun()

# ─── Ana Bileşen ───
st.markdown("""<div style='text-align:center; padding: 0.5rem 0 1rem;'>
    <h1 style='font-size: 2rem; margin:0;'>⚔️ Kılıç Reaksiyon Kronometresi</h1>
    <p style='color: #666; font-size: 0.9rem;'>Ses algıla → Kronometre başla → Space bas → Süre ölç</p>
</div>""", unsafe_allow_html=True)

component_html = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap');
    
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    
    body {{
        font-family: 'Inter', sans-serif;
        background: #0a0a0f;
        color: #fff;
        overflow: hidden;
        user-select: none;
    }}
    
    #app {{
        width: 100%;
        height: 600px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        position: relative;
        outline: none;
        cursor: default;
    }}
    
    /* ── Durum Başlığı ── */
    #status {{
        font-size: 1rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        margin-bottom: 1rem;
        transition: color 0.2s;
    }}
    
    /* ── Kronometre ── */
    #chrono {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 8rem;
        font-weight: 700;
        text-align: center;
        color: #333;
        text-shadow: none;
        transition: color 0.2s, text-shadow 0.3s;
        line-height: 1;
    }}
    
    #chrono.running {{
        color: #00FF88;
        text-shadow: 0 0 60px rgba(0, 255, 136, 0.3);
    }}
    
    #chrono.stopped {{
        color: #00AAFF;
        text-shadow: 0 0 40px rgba(0, 170, 255, 0.3);
    }}
    
    #unit {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.2rem;
        color: #555;
        margin-top: 0.5rem;
        letter-spacing: 0.1em;
    }}
    
    /* ── Ses Çubuğu ── */
    #mic-section {{
        margin-top: 2rem;
        text-align: center;
        width: 350px;
    }}
    
    #mic-label {{
        font-size: 0.75rem;
        color: #444;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-bottom: 0.5rem;
    }}
    
    #mic-bar-bg {{
        width: 100%;
        height: 12px;
        background: rgba(26, 31, 46, 0.8);
        border-radius: 6px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.04);
    }}
    
    #mic-bar {{
        height: 100%;
        width: 0%;
        border-radius: 6px;
        background: linear-gradient(90deg, #00FF88, #00AAFF);
        transition: width 0.05s linear;
    }}
    
    #mic-bar.loud {{
        background: linear-gradient(90deg, #FF9100, #FF1744);
    }}
    
    /* ── Talimat ── */
    #instruction {{
        position: absolute;
        bottom: 2.5rem;
        font-size: 0.85rem;
        color: #444;
        text-align: center;
    }}
    
    #instruction strong {{
        color: #888;
    }}
    
    /* ── Son Sonuç ── */
    #last-result {{
        margin-top: 1.5rem;
        font-size: 1rem;
        color: #555;
        min-height: 1.5rem;
    }}
    
    #last-result .rt-value {{
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        font-size: 1.3rem;
        color: #00FF88;
    }}
    
    /* ── Sayaç ── */
    #counter {{
        position: absolute;
        top: 1rem;
        right: 1.5rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        color: #333;
        background: rgba(26, 31, 46, 0.6);
        padding: 0.4rem 0.8rem;
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.04);
    }}

    /* ── Başlat Butonu ── */
    #start-btn {{
        padding: 1rem 2.5rem;
        font-size: 1.1rem;
        font-weight: 700;
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #00FF88, #00CC6A);
        color: #000;
        border: none;
        border-radius: 14px;
        cursor: pointer;
        animation: pulse 2s ease-in-out infinite;
    }}
    
    #start-btn:hover {{
        transform: scale(1.05);
        box-shadow: 0 0 30px rgba(0, 255, 136, 0.3);
    }}
    
    @keyframes pulse {{
        0%, 100% {{ transform: scale(1); }}
        50% {{ transform: scale(1.03); }}
    }}
    
    /* ── Ekran flaş ── */
    #flash {{
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.1s;
        border-radius: 0;
    }}
    
    .hidden {{ display: none !important; }}
</style>
</head>
<body>
<div id="app" tabindex="0">
    <div id="flash"></div>
    
    <!-- Başlangıç -->
    <div id="intro">
        <div style="font-size: 3rem; margin-bottom: 1rem;">🎤</div>
        <p style="color: #888; margin-bottom: 1.5rem; max-width: 400px; text-align: center; line-height: 1.6;">
            Mikrofon izni vererek başlayın.<br>
            <strong style="color:#00FF88">Ses algılandığında</strong> kronometre otomatik başlar.<br>
            <strong style="color:#00AAFF">Space tuşu</strong> ile durdurun.
        </p>
        <button id="start-btn" onclick="startListening()">🎤 Mikrofonu Aç ve Başla</button>
    </div>
    
    <!-- Ana Ekran -->
    <div id="main-screen" class="hidden">
        <div id="counter">Ölçüm: <span id="count-num">0</span></div>
        
        <div id="status">🎤 SES BEKLENİYOR...</div>
        
        <div id="chrono">0.000</div>
        <div id="unit">saniye</div>
        
        <div id="last-result"></div>
        
        <div id="mic-section">
            <div id="mic-label">🎤 Mikrofon Seviyesi</div>
            <div id="mic-bar-bg">
                <div id="mic-bar"></div>
            </div>
        </div>
        
        <div id="instruction">
            Antrenör <strong>"Allez!"</strong> desin → Kronometre başlar → <strong>SPACE</strong> tuşuna bas
        </div>
    </div>
</div>

<script>
    // ═══════════════════════════════════════
    //  DEĞİŞKENLER
    // ═══════════════════════════════════════
    let audioCtx = null;
    let analyser = null;
    let micStream = null;
    
    const THRESHOLD = {threshold};
    
    let isListening = false;    // mikrofon aktif mi
    let isRunning = false;      // kronometre çalışıyor mu
    let startTime = 0;          // kronometre başlangıç zamanı
    let chronoRAF = null;
    let measureCount = 0;
    let allResults = [];
    let cooldown = false;       // ses sonrası kısa bekleme

    // ── UI ──
    const $intro = document.getElementById('intro');
    const $main = document.getElementById('main-screen');
    const $status = document.getElementById('status');
    const $chrono = document.getElementById('chrono');
    const $micBar = document.getElementById('mic-bar');
    const $lastResult = document.getElementById('last-result');
    const $countNum = document.getElementById('count-num');
    const $flash = document.getElementById('flash');
    const $app = document.getElementById('app');

    // ═══════════════════════════════════════
    //  MİKROFON BAŞLAT
    // ═══════════════════════════════════════
    async function startListening() {{
        try {{
            // AudioContext
            const AC = window.AudioContext || window.webkitAudioContext;
            audioCtx = new AC();
            if (audioCtx.state === 'suspended') await audioCtx.resume();
            
            // Mikrofon izni
            micStream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
            
            // Analyser
            const source = audioCtx.createMediaStreamSource(micStream);
            analyser = audioCtx.createAnalyser();
            analyser.fftSize = 512;
            analyser.smoothingTimeConstant = 0.3;
            source.connect(analyser);
            
            isListening = true;
            
            // UI geçiş
            $intro.classList.add('hidden');
            $main.classList.remove('hidden');
            $app.focus();
            
            // Dinleme döngüsü başlat
            monitorAudio();
            
        }} catch(e) {{
            alert('Mikrofon erişimi reddedildi! Tarayıcı ayarlarından mikrofon iznini açın.');
        }}
    }}

    // ═══════════════════════════════════════
    //  SES İZLEME DÖNGÜSÜ
    // ═══════════════════════════════════════
    function monitorAudio() {{
        if (!analyser) return;
        
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        
        function loop() {{
            analyser.getByteFrequencyData(dataArray);
            
            // Ortalama ses seviyesi (0-1 arası)
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
            const avg = sum / dataArray.length / 255;
            
            // Ses çubuğu güncelle
            const pct = Math.min(avg * 500, 100);
            $micBar.style.width = pct + '%';
            $micBar.classList.toggle('loud', avg > THRESHOLD);
            
            // Ses eşiği aşıldı VE kronometre çalışmıyor VE cooldown yok
            if (avg > THRESHOLD && !isRunning && !cooldown) {{
                triggerStart();
            }}
            
            requestAnimationFrame(loop);
        }}
        loop();
    }}

    // ═══════════════════════════════════════
    //  KRONOMETREYİ BAŞLAT (Ses algılandı)
    // ═══════════════════════════════════════
    function triggerStart() {{
        isRunning = true;
        startTime = performance.now();
        
        // UI
        $status.textContent = '⏱️ ÇALIŞIYOR — SPACE BAS!';
        $status.style.color = '#00FF88';
        $chrono.className = 'running';
        
        // Yeşil flaş
        $flash.style.background = 'rgba(0, 255, 136, 0.15)';
        $flash.style.opacity = '1';
        setTimeout(() => {{ $flash.style.opacity = '0'; }}, 200);
        
        // Kronometre sayacı
        function tick() {{
            if (!isRunning) return;
            const elapsed = (performance.now() - startTime) / 1000;
            $chrono.textContent = elapsed.toFixed(3);
            chronoRAF = requestAnimationFrame(tick);
        }}
        tick();
    }}

    // ═══════════════════════════════════════
    //  KRONOMETREYİ DURDUR (Space basıldı)
    // ═══════════════════════════════════════
    function triggerStop() {{
        if (!isRunning) return;
        
        const stopTime = performance.now();
        const elapsed = stopTime - startTime;
        isRunning = false;
        
        if (chronoRAF) cancelAnimationFrame(chronoRAF);
        
        // Son değeri göster
        const seconds = (elapsed / 1000).toFixed(3);
        const ms = elapsed.toFixed(1);
        $chrono.textContent = seconds;
        $chrono.className = 'stopped';
        
        // Kaydet
        measureCount++;
        $countNum.textContent = measureCount;
        
        allResults.push({{
            number: measureCount,
            reaction_time_ms: parseFloat(ms),
            timestamp: Date.now()
        }});
        
        // Son sonuç göster
        $lastResult.innerHTML = 'Son: <span class="rt-value">' + ms + ' ms</span>';
        
        $status.textContent = '✅ KAYDEDILDI';
        $status.style.color = '#00AAFF';
        
        // Mavi flaş
        $flash.style.background = 'rgba(0, 170, 255, 0.15)';
        $flash.style.opacity = '1';
        setTimeout(() => {{ $flash.style.opacity = '0'; }}, 200);
        
        // Streamlit'e gönder
        window.parent.postMessage({{
            isStreamlitMessage: true,
            type: 'streamlit:setComponentValue',
            value: {{
                status: 'RESULT',
                count: measureCount,
                reaction_time_ms: parseFloat(ms),
                all_results: allResults
            }}
        }}, '*');
        
        // Cooldown: 2 saniye bekle sonra tekrar dinle
        cooldown = true;
        setTimeout(() => {{
            cooldown = false;
            $chrono.textContent = '0.000';
            $chrono.className = '';
            $status.textContent = '🎤 SES BEKLENİYOR...';
            $status.style.color = '#888';
        }}, 2000);
    }}

    // ═══════════════════════════════════════
    //  KLAVYE DİNLEYİCİ
    // ═══════════════════════════════════════
    document.addEventListener('keydown', (e) => {{
        if (e.code === 'Space' || e.code === 'Enter') {{
            e.preventDefault();
            if (e.repeat) return;
            if (isRunning) {{
                triggerStop();
            }}
        }}
    }}, {{ passive: false, capture: true }});
    
    // Tıklama ile de durdurabilsin
    $app.addEventListener('click', () => {{
        if (isRunning) {{
            triggerStop();
        }}
    }});

    // Focus
    $app.focus();
    
    // Streamlit bridge
    window.parent.postMessage({{ isStreamlitMessage: true, type: 'streamlit:componentReady', apiVersion: 1 }}, '*');
    window.parent.postMessage({{ isStreamlitMessage: true, type: 'streamlit:setFrameHeight', height: 620 }}, '*');
</script>
</body>
</html>
"""

import streamlit.components.v1 as components
result = components.html(component_html, height=620, scrolling=False)

# ─── Sonuçlar Tablosu ───
st.markdown("---")

if st.session_state.results:
    st.markdown("### ⏱️ Ölçüm Sonuçları")
    
    df = pd.DataFrame(st.session_state.results)
    
    # Metrikler
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ölçüm Sayısı", len(df))
    c2.metric("Ort. RT", f"{df['reaction_time_ms'].mean():.0f} ms")
    c3.metric("En Hızlı", f"{df['reaction_time_ms'].min():.0f} ms")
    c4.metric("En Yavaş", f"{df['reaction_time_ms'].max():.0f} ms")
    
    # Grafik
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["number"],
        y=df["reaction_time_ms"],
        mode='lines+markers',
        marker=dict(size=10, color='#00FF88'),
        line=dict(width=2, color='#00FF88'),
    ))
    fig.update_layout(
        title="Reaksiyon Süreleri",
        xaxis_title="Ölçüm No",
        yaxis_title="ms",
        template="plotly_dark",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(10,10,15,0.8)',
        margin=dict(l=40, r=20, t=50, b=40)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # İndirme
    csv = df.to_csv(index=False).encode('utf-8')
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    athlete = st.session_state.athlete_name or "sporcu"
    st.download_button("📥 CSV İndir", csv, f"kilicRT_{athlete}_{ts}.csv", "text/csv", use_container_width=True)
else:
    st.info("👆 Yukarıda mikrofonu açın, antrenör ses versin, Space ile durdurun. Sonuçlar burada görünecek.")
