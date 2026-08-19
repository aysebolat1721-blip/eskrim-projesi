import streamlit as st
import os
import datetime
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(
    page_title="Eskrim Kılıç - Reaksiyon Kronometresi",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

if "athlete_name" not in st.session_state:
    st.session_state.athlete_name = ""
if "results" not in st.session_state:
    st.session_state.results = []

with st.sidebar:
    st.markdown("### 🤺 Sporcu")
    name = st.text_input("Ad Soyad", value=st.session_state.athlete_name)
    if name:
        st.session_state.athlete_name = name
    st.markdown("### 🎤 Ses Hassasiyeti")
    threshold = st.slider("Eşik", 0.01, 0.50, 0.08, 0.01,
                          help="Düşük = daha hassas")
    st.divider()
    if st.session_state.results:
        if st.button("🗑️ Sonuçları Temizle", use_container_width=True):
            st.session_state.results = []
            st.rerun()

st.markdown("""<div style='text-align:center; padding: 0.5rem 0 1rem;'>
    <h1 style='font-size: 2rem; margin:0;'>⚔️ Kılıç Reaksiyon Kronometresi</h1>
    <p style='color: #666; font-size: 0.9rem;'>En Garde → Prêts → Allez! → Space bas</p>
</div>""", unsafe_allow_html=True)

component_html = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap');
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family:'Inter',sans-serif; background:#0a0a0f; color:#fff; overflow:hidden; user-select:none; }}

    #app {{
        width:100%; height:620px;
        display:flex; flex-direction:column; align-items:center; justify-content:center;
        position:relative; outline:none;
    }}

    /* Faz göstergesi */
    #phase {{
        font-size: 6rem; font-weight: 900;
        text-align:center; line-height:1;
        transition: color 0.2s, text-shadow 0.3s;
        color: #333;
    }}

    #phase.engarde {{
        color: #fff;
        text-shadow: 0 0 40px rgba(255,255,255,0.2);
    }}
    #phase.prets {{
        color: #FFC107;
        text-shadow: 0 0 50px rgba(255,193,7,0.3);
    }}
    #phase.allez {{
        color: #00FF88;
        text-shadow: 0 0 60px rgba(0,255,136,0.4);
    }}
    #phase.stopped {{
        color: #00AAFF;
        text-shadow: 0 0 40px rgba(0,170,255,0.3);
    }}

    /* Alt durum */
    #status {{
        font-size: 1rem; font-weight: 600;
        color: #555; margin-top: 0.8rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        transition: color 0.2s;
    }}

    /* Kronometre */
    #chrono {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 5rem; font-weight: 700;
        color: #222; margin-top: 1rem;
        text-shadow: none;
        transition: color 0.2s, text-shadow 0.3s;
    }}
    #chrono.running {{
        color: #00FF88;
        text-shadow: 0 0 50px rgba(0,255,136,0.3);
    }}
    #chrono.stopped {{
        color: #00AAFF;
        text-shadow: 0 0 30px rgba(0,170,255,0.2);
    }}

    #unit {{ font-size:0.9rem; color:#444; margin-top:0.3rem; font-family:'JetBrains Mono',monospace; }}

    /* Son sonuç */
    #last-result {{
        margin-top:1rem; font-size:1rem; color:#555; min-height:1.5rem;
    }}
    #last-result .rt {{ font-family:'JetBrains Mono',monospace; font-weight:700; font-size:1.3rem; color:#00FF88; }}

    /* Ses çubuğu */
    #mic-section {{ margin-top:1.5rem; text-align:center; width:300px; }}
    #mic-lbl {{ font-size:0.7rem; color:#444; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.4rem; }}
    #mic-bg {{ width:100%; height:10px; background:rgba(26,31,46,0.8); border-radius:5px; overflow:hidden; border:1px solid rgba(255,255,255,0.04); }}
    #mic-fill {{ height:100%; width:0%; border-radius:5px; background:linear-gradient(90deg,#00FF88,#00AAFF); transition:width 0.05s linear; }}
    #mic-fill.loud {{ background:linear-gradient(90deg,#FF9100,#FF1744); }}

    /* Adımlar göstergesi */
    #steps {{
        position:absolute; top:1.2rem; left:50%; transform:translateX(-50%);
        display:flex; gap:0.5rem; align-items:center;
    }}
    .step {{
        width:12px; height:12px; border-radius:50%;
        background:#1a1f2e; border:2px solid #333;
        transition: all 0.3s;
    }}
    .step.active {{ border-color:#FFC107; background:#FFC107; box-shadow:0 0 10px rgba(255,193,7,0.4); }}
    .step.done {{ border-color:#00FF88; background:#00FF88; box-shadow:0 0 10px rgba(0,255,136,0.3); }}
    .step-line {{ width:30px; height:2px; background:#222; }}

    /* Sayaç */
    #counter {{
        position:absolute; top:1rem; right:1.5rem;
        font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:#333;
        background:rgba(26,31,46,0.6); padding:0.4rem 0.8rem; border-radius:8px;
        border:1px solid rgba(255,255,255,0.04);
    }}

    /* Talimat */
    #instruction {{
        position:absolute; bottom:2rem;
        font-size:0.8rem; color:#383838; text-align:center;
    }}
    #instruction strong {{ color:#555; }}

    /* Başlat */
    #start-btn {{
        padding:1rem 2.5rem; font-size:1.1rem; font-weight:700;
        font-family:'Inter',sans-serif;
        background:linear-gradient(135deg,#00FF88,#00CC6A);
        color:#000; border:none; border-radius:14px; cursor:pointer;
        animation:pulse 2s ease-in-out infinite;
    }}
    #start-btn:hover {{ transform:scale(1.05); box-shadow:0 0 30px rgba(0,255,136,0.3); }}

    /* Flash */
    #flash {{
        position:absolute; top:0;left:0;right:0;bottom:0;
        pointer-events:none; opacity:0; transition:opacity 0.15s;
    }}

    .hidden {{ display:none !important; }}
    @keyframes pulse {{ 0%,100%{{transform:scale(1);}} 50%{{transform:scale(1.03);}} }}
</style>
</head>
<body>
<div id="app" tabindex="0">
    <div id="flash"></div>

    <!-- INTRO -->
    <div id="intro">
        <div style="font-size:3rem; margin-bottom:1rem;">🎤⚔️</div>
        <p style="color:#888; margin-bottom:1.5rem; max-width:420px; text-align:center; line-height:1.7;">
            Antrenör sırayla komut verir:<br>
            <strong style="color:#fff">1.</strong> "En Garde" →
            <strong style="color:#FFC107">2.</strong> "Prêts" →
            <strong style="color:#00FF88">3.</strong> "Allez!" → ⏱️ kronometre başlar<br>
            Sporcu <strong style="color:#00AAFF">SPACE</strong> tuşuyla durdurur.
        </p>
        <button id="start-btn" onclick="startApp()">🎤 Mikrofonu Aç ve Başla</button>
    </div>

    <!-- ANA EKRAN -->
    <div id="main-screen" class="hidden">
        <!-- Adım göstergesi -->
        <div id="steps">
            <div class="step" id="s1"></div>
            <div class="step-line"></div>
            <div class="step" id="s2"></div>
            <div class="step-line"></div>
            <div class="step" id="s3"></div>
        </div>

        <div id="counter">Ölçüm: <span id="cnt">0</span></div>

        <div id="phase">⚔️</div>
        <div id="status">🎤 "En Garde" komutunu bekliyor...</div>
        <div id="chrono">0.000</div>
        <div id="unit">saniye</div>
        <div id="last-result"></div>

        <div id="mic-section">
            <div id="mic-lbl">🎤 Mikrofon Seviyesi</div>
            <div id="mic-bg"><div id="mic-fill"></div></div>
        </div>

        <div id="instruction">
            Antrenör: <strong>En Garde</strong> → <strong>Prêts</strong> → <strong>Allez!</strong> &nbsp;|&nbsp; Sporcu: <strong>SPACE</strong> bas
        </div>
    </div>
</div>

<script>
    // ═════════════════════════
    //  DEĞİŞKENLER
    // ═════════════════════════
    const TH = {threshold};

    let audioCtx, analyser, micStream;
    let currentStep = 0;   // 0=bekle engarde, 1=bekle prets, 2=bekle allez, 3=kronometre çalışıyor
    let isRunning = false;
    let startTime = 0;
    let chronoRAF = null;
    let measureCount = 0;
    let allResults = [];
    let cooldown = false;
    let soundWasLow = true; // her komut için ses düşüp yükselmeli

    const $intro = document.getElementById('intro');
    const $main = document.getElementById('main-screen');
    const $phase = document.getElementById('phase');
    const $status = document.getElementById('status');
    const $chrono = document.getElementById('chrono');
    const $micFill = document.getElementById('mic-fill');
    const $lastResult = document.getElementById('last-result');
    const $cnt = document.getElementById('cnt');
    const $flash = document.getElementById('flash');
    const $app = document.getElementById('app');
    const $s1 = document.getElementById('s1');
    const $s2 = document.getElementById('s2');
    const $s3 = document.getElementById('s3');

    // ═════════════════════════
    //  BAŞLAT
    // ═════════════════════════
    async function startApp() {{
        try {{
            const AC = window.AudioContext || window.webkitAudioContext;
            audioCtx = new AC();
            if (audioCtx.state === 'suspended') await audioCtx.resume();

            micStream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
            const source = audioCtx.createMediaStreamSource(micStream);
            analyser = audioCtx.createAnalyser();
            analyser.fftSize = 512;
            analyser.smoothingTimeConstant = 0.3;
            source.connect(analyser);

            $intro.classList.add('hidden');
            $main.classList.remove('hidden');
            $app.focus();

            resetToWaiting();
            monitorLoop();
        }} catch(e) {{
            alert('Mikrofon erişimi reddedildi!');
        }}
    }}

    // ═════════════════════════
    //  SES İZLEME
    // ═════════════════════════
    function monitorLoop() {{
        const buf = new Uint8Array(analyser.frequencyBinCount);

        function tick() {{
            analyser.getByteFrequencyData(buf);
            let sum = 0;
            for (let i = 0; i < buf.length; i++) sum += buf[i];
            const avg = sum / buf.length / 255;

            // Çubuk
            const pct = Math.min(avg * 500, 100);
            $micFill.style.width = pct + '%';
            $micFill.classList.toggle('loud', avg > TH);

            // Ses düştüyse bayrak
            if (avg < TH * 0.5) {{
                soundWasLow = true;
            }}

            // Yeni ses algıla (düşükten yükseğe geçiş)
            if (avg > TH && soundWasLow && !cooldown && !isRunning) {{
                soundWasLow = false;
                handleVoiceDetected();
            }}

            requestAnimationFrame(tick);
        }}
        tick();
    }}

    // ═════════════════════════
    //  SES ALGILANDI
    // ═════════════════════════
    function handleVoiceDetected() {{
        if (currentStep === 0) {{
            // ── EN GARDE ──
            currentStep = 1;
            $s1.className = 'step active';
            $phase.textContent = '⚔️ EN GARDE';
            $phase.className = 'engarde';
            $status.textContent = '🎤 "Prêts" komutunu bekliyor...';
            $status.style.color = '#aaa';
            flash('#ffffff', 0.08);

            // Kısa cooldown (aynı ses tekrar tetiklemesin)
            cooldown = true;
            setTimeout(() => {{ cooldown = false; }}, 800);

        }} else if (currentStep === 1) {{
            // ── PRÊTS ──
            currentStep = 2;
            $s1.className = 'step done';
            $s2.className = 'step active';
            $phase.textContent = '🟡 PRÊTS';
            $phase.className = 'prets';
            $status.textContent = '🎤 "Allez!" komutunu bekliyor...';
            $status.style.color = '#FFC107';
            flash('#FFC107', 0.1);

            cooldown = true;
            setTimeout(() => {{ cooldown = false; }}, 800);

        }} else if (currentStep === 2) {{
            // ── ALLEZ! → KRONOMETREYİ BAŞLAT ──
            currentStep = 3;
            isRunning = true;
            startTime = performance.now();

            $s2.className = 'step done';
            $s3.className = 'step active';
            $phase.textContent = '🟢 ALLEZ!';
            $phase.className = 'allez';
            $status.textContent = '⏱️ SPACE BAS!';
            $status.style.color = '#00FF88';
            $chrono.className = 'running';
            flash('#00FF88', 0.15);

            // Kronometre tick
            function chronoTick() {{
                if (!isRunning) return;
                const t = (performance.now() - startTime) / 1000;
                $chrono.textContent = t.toFixed(3);
                chronoRAF = requestAnimationFrame(chronoTick);
            }}
            chronoTick();
        }}
    }}

    // ═════════════════════════
    //  SPACE → DURDUR
    // ═════════════════════════
    function stopChrono() {{
        if (!isRunning) return;
        const elapsed = performance.now() - startTime;
        isRunning = false;
        if (chronoRAF) cancelAnimationFrame(chronoRAF);

        const sec = (elapsed / 1000).toFixed(3);
        const ms = elapsed.toFixed(1);
        $chrono.textContent = sec;
        $chrono.className = 'stopped';
        $s3.className = 'step done';
        $phase.textContent = '✅ ' + ms + ' ms';
        $phase.className = 'stopped';
        $status.textContent = 'kaydedildi';
        $status.style.color = '#00AAFF';
        flash('#00AAFF', 0.12);

        measureCount++;
        $cnt.textContent = measureCount;
        $lastResult.innerHTML = 'Son: <span class="rt">' + ms + ' ms</span>';

        allResults.push({{
            number: measureCount,
            reaction_time_ms: parseFloat(ms),
            timestamp: Date.now()
        }});

        // Streamlit'e gönder
        window.parent.postMessage({{
            isStreamlitMessage: true,
            type: 'streamlit:setComponentValue',
            value: {{ status:'RESULT', count:measureCount, reaction_time_ms:parseFloat(ms), all_results:allResults }}
        }}, '*');

        // 2.5 sn sonra sıfırla
        cooldown = true;
        setTimeout(() => {{
            cooldown = false;
            resetToWaiting();
        }}, 2500);
    }}

    // ═════════════════════════
    //  SIFIRLA
    // ═════════════════════════
    function resetToWaiting() {{
        currentStep = 0;
        isRunning = false;
        soundWasLow = true;
        $s1.className = 'step';
        $s2.className = 'step';
        $s3.className = 'step';
        $phase.textContent = '⚔️';
        $phase.className = '';
        $chrono.textContent = '0.000';
        $chrono.className = '';
        $status.textContent = '🎤 "En Garde" komutunu bekliyor...';
        $status.style.color = '#555';
    }}

    // ═════════════════════════
    //  FLASH
    // ═════════════════════════
    function flash(color, alpha) {{
        $flash.style.background = color.replace(')', ',' + alpha + ')').replace('rgb', 'rgba').replace('#', '');
        // hex to rgba
        $flash.style.background = hexToRgba(color, alpha);
        $flash.style.opacity = '1';
        setTimeout(() => {{ $flash.style.opacity = '0'; }}, 250);
    }}

    function hexToRgba(hex, a) {{
        const r = parseInt(hex.slice(1,3),16);
        const g = parseInt(hex.slice(3,5),16);
        const b = parseInt(hex.slice(5,7),16);
        return 'rgba('+r+','+g+','+b+','+a+')';
    }}

    // ═════════════════════════
    //  KLAVYE
    // ═════════════════════════
    document.addEventListener('keydown', (e) => {{
        if (e.code === 'Space' || e.code === 'Enter') {{
            e.preventDefault();
            if (e.repeat) return;
            stopChrono();
        }}
    }}, {{ passive:false, capture:true }});

    $app.addEventListener('click', () => {{ if(isRunning) stopChrono(); }});
    $app.focus();

    window.parent.postMessage({{ isStreamlitMessage:true, type:'streamlit:componentReady', apiVersion:1 }}, '*');
    window.parent.postMessage({{ isStreamlitMessage:true, type:'streamlit:setFrameHeight', height:640 }}, '*');
</script>
</body>
</html>
"""

import streamlit.components.v1 as components
components.html(component_html, height=640, scrolling=False)

# ─── Sonuçlar ───
st.markdown("---")
if st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ölçüm", len(df))
    c2.metric("Ort. RT", f"{{df['reaction_time_ms'].mean():.0f}} ms")
    c3.metric("En Hızlı", f"{{df['reaction_time_ms'].min():.0f}} ms")
    c4.metric("En Yavaş", f"{{df['reaction_time_ms'].max():.0f}} ms")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["number"], y=df["reaction_time_ms"],
        mode='lines+markers', marker=dict(size=10, color='#00FF88'), line=dict(width=2, color='#00FF88')))
    fig.update_layout(title="Reaksiyon Süreleri", xaxis_title="Ölçüm", yaxis_title="ms",
        template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(10,10,15,0.8)', margin=dict(l=40,r=20,t=50,b=40))
    st.plotly_chart(fig, use_container_width=True)

    csv = df.to_csv(index=False).encode('utf-8')
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    athlete = st.session_state.athlete_name or "sporcu"
    st.download_button("📥 CSV İndir", csv, f"kilicRT_{{athlete}}_{{ts}}.csv", "text/csv", use_container_width=True)
else:
    st.info("👆 Mikrofonu açın → Antrenör: En Garde, Prêts, Allez! → Sporcu: SPACE bas")
