import streamlit as st
import os
import json
import datetime
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

# ─── Sayfa Ayarları ───
st.set_page_config(
    page_title="Eskrim Kılıç - Go/No-Go Reaksiyon Sistemi",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CSS Yükle ───
css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─── Session State Başlat ───
defaults = {
    "athlete_name": "",
    "test_mode": "poule",
    "test_history": [],
    "current_results": None,
    "page": "anasayfa",
    "sound_enabled": True,
    "custom_settings": {
        "go_ratio": 70,
        "min_jitter": 1500,
        "max_jitter": 4500,
        "target_hits": 20,
        "response_timeout": 1000,
    }
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── Sidebar ───
with st.sidebar:
    st.markdown("""<div style='text-align:center; padding: 1rem 0;'>
        <div style='font-size: 3rem;'>⚔️</div>
        <h2 style='margin: 0.3rem 0; font-size: 1.5rem;'>KILICI</h2>
        <p style='color: #00FF88; font-size: 0.75rem; letter-spacing: 0.15em; text-transform: uppercase;'>Go/No-Go Reaksiyon Sistemi</p>
        <p style='color: #555; font-size: 0.7rem; margin-top: 0.3rem;'>Sabre • Kılıç Branşı</p>
    </div>""", unsafe_allow_html=True)
    
    st.divider()
    
    page = st.radio(
        "Sayfa",
        ["🏠 Anasayfa", "⚔️ Antrenman", "📊 Sonuçlar", "⚙️ Ayarlar"],
        label_visibility="collapsed"
    )
    
    st.divider()
    
    if st.session_state.athlete_name:
        st.markdown(f"🤺 **{st.session_state.athlete_name}**")
        mode_labels = {"poule": "Poule (5 Tuş)", "elimination": "Eliminasyon (15 Tuş)", "custom": "Serbest Atölye"}
        st.markdown(f"📋 {mode_labels.get(st.session_state.test_mode, '')}")
    
    st.markdown("""<div style='position: fixed; bottom: 1rem; color: #333; font-size: 0.65rem;'>
        v1.0 • Kılıç Branşı
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  SAYFA: ANASAYFA
# ═══════════════════════════════════════════════════════════════
if page == "🏠 Anasayfa":
    st.markdown("""<div class='fade-in' style='text-align: center; padding: 1rem 0 2rem;'>
        <div class='hero-title'>⚔️ Kılıç Go/No-Go</div>
        <div class='hero-subtitle'>Bilişsel Reaksiyon ve Dürtü Kontrolü Antrenman Sistemi</div>
    </div>""", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🤺 Sporcu Bilgileri")
        name = st.text_input("Sporcu Adı Soyadı", value=st.session_state.athlete_name, placeholder="Adınızı girin...")
        
        hand = st.radio("Dominant El", ["Sağ", "Sol"], horizontal=True)
        
        if st.button("💾 Kaydet", use_container_width=True):
            st.session_state.athlete_name = name
            st.session_state.athlete_hand = hand
            st.success(f"✅ Kaydedildi: {name}")
    
    with col2:
        st.markdown("### 📋 Antrenman Modu")
        
        st.markdown("""<div class='mode-card'>
            <div class='mode-icon'>🏅</div>
            <div class='mode-title'>Poule Modu</div>
            <div class='mode-desc'>5 başarılı vuruşa kadar<br>Hızlı seri reaksiyon analizi</div>
        </div>""", unsafe_allow_html=True)
        if st.button("Poule Seç (5 Tuş)", use_container_width=True, key="btn_poule"):
            st.session_state.test_mode = "poule"
            st.success("✅ Poule Modu seçildi")
        
        st.markdown("""<div class='mode-card'>
            <div class='mode-icon'>🏆</div>
            <div class='mode-title'>Direkt Eliminasyon</div>
            <div class='mode-desc'>15 başarılı vuruşa kadar<br>Bilişsel yorgunluk analizi</div>
        </div>""", unsafe_allow_html=True)
        if st.button("Eliminasyon Seç (15 Tuş)", use_container_width=True, key="btn_elim"):
            st.session_state.test_mode = "elimination"
            st.success("✅ Eliminasyon Modu seçildi")
        
        st.markdown("""<div class='mode-card'>
            <div class='mode-icon'>🔧</div>
            <div class='mode-title'>Serbest Atölye</div>
            <div class='mode-desc'>Özelleştirilebilir ayarlar<br>Antrenör kontrolü</div>
        </div>""", unsafe_allow_html=True)
        if st.button("Serbest Atölye Seç", use_container_width=True, key="btn_custom"):
            st.session_state.test_mode = "custom"
            st.success("✅ Serbest Atölye seçildi")


# ═══════════════════════════════════════════════════════════════
#  SAYFA: ANTRENMAN (Ses Algılama + Kronometre)
# ═══════════════════════════════════════════════════════════════
elif page == "⚔️ Antrenman":
    if not st.session_state.athlete_name:
        st.warning("⚠️ Önce Anasayfa'dan sporcu bilgilerinizi girin!")
        st.stop()
    
    mode = st.session_state.test_mode
    mode_labels = {"poule": "Poule (5 Tuş)", "elimination": "Eliminasyon (15 Tuş)", "custom": "Serbest Atölye"}
    
    st.markdown(f"""<div style='text-align: center; margin-bottom: 1rem;'>
        <span style='color: #00FF88; font-size: 0.8rem; letter-spacing: 0.1em;'>ANTRENMAN MODU</span>
        <h2 style='margin: 0.3rem 0;'>⚔️ {mode_labels[mode]}</h2>
        <span style='color: #666;'>{st.session_state.athlete_name}</span>
    </div>""", unsafe_allow_html=True)
    
    # ─── Mod Ayarları ───
    if mode == "poule":
        target_hits = 5
        go_ratio = 0.70
        settings = st.session_state.custom_settings
    elif mode == "elimination":
        target_hits = 15
        go_ratio = 0.70
        settings = st.session_state.custom_settings
    else:
        settings = st.session_state.custom_settings
        target_hits = settings["target_hits"]
        go_ratio = settings["go_ratio"] / 100.0
    
    min_jitter = settings.get("min_jitter", 1500)
    max_jitter = settings.get("max_jitter", 4500)
    response_timeout = settings.get("response_timeout", 1000)
    sound_enabled = st.session_state.sound_enabled

    # ─── JavaScript Go/No-Go Motoru (Ses Algılama + Kronometre) ───
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
        }}
        
        #app {{
            width: 100%;
            min-height: 650px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            position: relative;
        }}
        
        /* ── Başlangıç Ekranı ── */
        #start-screen {{
            text-align: center;
            animation: fadeIn 0.8s ease;
        }}
        
        #start-screen h1 {{
            font-size: 2.5rem;
            font-weight: 900;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #00FF88, #00AAFF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        #start-screen .subtitle {{
            color: #666;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
        }}
        
        .instructions {{
            background: rgba(26, 31, 46, 0.6);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 16px;
            padding: 1.5rem;
            margin: 1.5rem auto;
            max-width: 500px;
            text-align: left;
        }}
        
        .instructions li {{
            color: #aaa;
            font-size: 0.85rem;
            margin: 0.5rem 0;
            line-height: 1.5;
        }}
        
        .instructions li strong {{
            color: #00FF88;
        }}
        
        #start-btn {{
            padding: 1rem 3rem;
            font-size: 1.2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #00FF88, #00CC6A);
            color: #000;
            border: none;
            border-radius: 16px;
            cursor: pointer;
            margin-top: 1.5rem;
            animation: pulse 2s ease-in-out infinite;
            transition: all 0.3s;
        }}
        
        #start-btn:hover {{
            transform: scale(1.05);
            box-shadow: 0 0 40px rgba(0, 255, 136, 0.3);
        }}
        
        /* ── Deneme Ekranı ── */
        #trial-screen {{
            display: none;
            width: 100%;
            min-height: 650px;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            position: relative;
            transition: background 0.15s ease;
        }}
        
        #hud {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            display: flex;
            justify-content: space-between;
            padding: 1rem 1.5rem;
            z-index: 10;
        }}
        
        .hud-item {{
            background: rgba(0,0,0,0.5);
            padding: 0.5rem 1rem;
            border-radius: 10px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            border: 1px solid rgba(255,255,255,0.06);
        }}
        
        .hud-hits {{
            color: #00FF88;
        }}
        
        .hud-trial {{
            color: #888;
        }}
        
        /* ── Ana Gösterge ── */
        #phase-text {{
            font-size: 5rem;
            font-weight: 900;
            text-align: center;
            text-shadow: 0 0 40px currentColor;
            transition: all 0.15s ease;
        }}
        
        #sub-text {{
            font-size: 1.2rem;
            color: #666;
            text-align: center;
            margin-top: 1rem;
        }}
        
        /* ── Kronometre ── */
        #chrono {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 4rem;
            font-weight: 700;
            color: #00FF88;
            text-align: center;
            margin-top: 1.5rem;
            text-shadow: 0 0 30px rgba(0, 255, 136, 0.3);
            opacity: 0;
            transition: opacity 0.3s;
        }}
        
        #chrono.visible {{
            opacity: 1;
        }}
        
        /* ── Ses Göstergesi ── */
        #audio-indicator {{
            position: absolute;
            bottom: 5rem;
            left: 50%;
            transform: translateX(-50%);
            text-align: center;
            width: 300px;
        }}
        
        #audio-bar-container {{
            width: 100%;
            height: 8px;
            background: rgba(26, 31, 46, 0.8);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 0.5rem;
        }}
        
        #audio-bar {{
            height: 100%;
            width: 0%;
            border-radius: 4px;
            background: linear-gradient(90deg, #00FF88, #00AAFF, #FF1744);
            transition: width 0.05s linear;
        }}
        
        #audio-label {{
            font-size: 0.7rem;
            color: #444;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 0.3rem;
        }}
        
        #mic-status {{
            font-size: 0.75rem;
            color: #555;
            margin-top: 0.3rem;
        }}
        
        /* ── İlerleme Çubuğu ── */
        #progress-bar {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: rgba(26, 31, 46, 0.5);
        }}
        
        #progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #00FF88, #00AAFF);
            border-radius: 0 2px 2px 0;
            transition: width 0.3s ease;
            width: 0%;
        }}
        
        /* ── Bitiş Ekranı ── */
        #end-screen {{
            display: none;
            text-align: center;
            animation: fadeIn 0.8s ease;
        }}
        
        #end-screen h1 {{
            font-size: 2.5rem;
            font-weight: 900;
            color: #00FF88;
            margin-bottom: 1rem;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin: 2rem auto;
            max-width: 500px;
        }}
        
        .summary-item {{
            background: rgba(26, 31, 46, 0.7);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 12px;
            padding: 1rem;
        }}
        
        .summary-value {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.8rem;
            font-weight: 700;
            color: #00FF88;
        }}
        
        .summary-label {{
            font-size: 0.7rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 0.3rem;
        }}
        
        /* ── Animasyonlar ── */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.03); }}
        }}
        
        @keyframes glow-green {{
            0%, 100% {{ box-shadow: 0 0 20px rgba(0,255,136,0.2); }}
            50% {{ box-shadow: 0 0 60px rgba(0,255,136,0.4); }}
        }}
    </style>
    </head>
    <body>
    <div id="app">
        <!-- BAŞLANGIÇ -->
        <div id="start-screen">
            <h1>⚔️ KILIÇ GO/NO-GO</h1>
            <div class="subtitle">{mode_labels[mode]} • {st.session_state.athlete_name}</div>
            <div class="instructions">
                <ul>
                    <li>🎤 <strong>Mikrofon</strong> ile sesiniz algılanır (Allez komutu gibi)</li>
                    <li>⌨️ <strong>Space / Enter</strong> tuşu ile de vuruş yapabilirsiniz</li>
                    <li>🟢 <strong>ALLEZ!</strong> → Hemen vurun (ses veya tuş)</li>
                    <li>🔴 <strong>DUR!</strong> → Hiçbir şey yapmayın, bekleyin</li>
                    <li>⏱️ Kronometre reaksiyon sürenizi milisaniye olarak ölçer</li>
                    <li>⚠️ Erken hamle = dürtü kontrolü hatası</li>
                </ul>
            </div>
            <button id="start-btn" onclick="startTest()">🤺 BAŞLA</button>
        </div>
        
        <!-- DENEME -->
        <div id="trial-screen">
            <div id="hud">
                <div class="hud-item hud-trial">Deneme: <span id="trial-num">0</span></div>
                <div class="hud-item hud-hits">Tuş: <span id="hit-count">0</span> / <span id="target-count">{target_hits}</span></div>
            </div>
            
            <div id="phase-text"></div>
            <div id="sub-text"></div>
            <div id="chrono">0.000</div>
            
            <div id="audio-indicator">
                <div id="audio-label">🎤 Mikrofon</div>
                <div id="audio-bar-container">
                    <div id="audio-bar"></div>
                </div>
                <div id="mic-status">Bekleniyor...</div>
            </div>
            
            <div id="progress-bar">
                <div id="progress-fill"></div>
            </div>
        </div>
        
        <!-- BİTİŞ -->
        <div id="end-screen">
            <h1>✅ TEST TAMAMLANDI!</h1>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-value" id="sum-rt">-</div>
                    <div class="summary-label">Ort. RT (ms)</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value" id="sum-hits">-</div>
                    <div class="summary-label">İsabet</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value" id="sum-impulse">-</div>
                    <div class="summary-label">Dürtü Kontrol %</div>
                </div>
            </div>
            <p style="color: #555; font-size: 0.85rem;">Sonuçlar otomatik kaydedildi. 📊 Sonuçlar sayfasından detaylı analizi görün.</p>
        </div>
    </div>
    
    <script>
    // ═══════════════════════════════════════════
    //  STREAMLIT BRIDGE
    // ═══════════════════════════════════════════
    const Bridge = {{
        sendReady() {{
            window.parent.postMessage({{ isStreamlitMessage: true, type: 'streamlit:componentReady', apiVersion: 1 }}, '*');
        }},
        setHeight(h) {{
            window.parent.postMessage({{ isStreamlitMessage: true, type: 'streamlit:setFrameHeight', height: h || 700 }}, '*');
        }},
        sendData(data) {{
            window.parent.postMessage({{ isStreamlitMessage: true, type: 'streamlit:setComponentValue', value: data }}, '*');
        }}
    }};
    Bridge.sendReady();
    Bridge.setHeight(700);
    
    // ═══════════════════════════════════════════
    //  SES SİSTEMİ (Web Audio API)
    // ═══════════════════════════════════════════
    class AudioManager {{
        constructor() {{
            this.ctx = null;
            this.micStream = null;
            this.analyser = null;
            this.micEnabled = false;
            this.volumeThreshold = 0.15;
            this.onMicTrigger = null;
            this._monitorRAF = null;
        }}
        
        init() {{
            const AC = window.AudioContext || window.webkitAudioContext;
            this.ctx = new AC();
            if (this.ctx.state === 'suspended') this.ctx.resume();
        }}
        
        playTone(freq, dur, type='sine') {{
            if (!this.ctx) return;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = type;
            osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
            gain.gain.setValueAtTime(0.001, this.ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.25, this.ctx.currentTime + 0.01);
            gain.gain.exponentialRampToValueAtTime(0.0001, this.ctx.currentTime + dur);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(this.ctx.currentTime);
            osc.stop(this.ctx.currentTime + dur);
        }}
        
        playEnGarde() {{ this.playTone(400, 0.3, 'sine'); }}
        playPrets()   {{ this.playTone(600, 0.2, 'sine'); }}
        playAllez()   {{ this.playTone(1000, 0.08, 'sine'); }}
        playHalt()    {{ this.playTone(300, 0.15, 'triangle'); }}
        playError()   {{ this.playTone(150, 0.25, 'sawtooth'); }}
        playSuccess() {{ this.playTone(880, 0.1, 'sine'); }}
        
        async initMicrophone() {{
            try {{
                this.micStream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                const source = this.ctx.createMediaStreamSource(this.micStream);
                this.analyser = this.ctx.createAnalyser();
                this.analyser.fftSize = 512;
                this.analyser.smoothingTimeConstant = 0.3;
                source.connect(this.analyser);
                this.micEnabled = true;
                this._startMonitor();
                document.getElementById('mic-status').textContent = '✅ Mikrofon aktif';
                document.getElementById('mic-status').style.color = '#00FF88';
                return true;
            }} catch(e) {{
                document.getElementById('mic-status').textContent = '❌ Mikrofon erişimi reddedildi';
                document.getElementById('mic-status').style.color = '#FF1744';
                this.micEnabled = false;
                return false;
            }}
        }}
        
        _startMonitor() {{
            if (!this.analyser) return;
            const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
            const bar = document.getElementById('audio-bar');
            
            const monitor = () => {{
                this.analyser.getByteFrequencyData(dataArray);
                let sum = 0;
                for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
                const avg = sum / dataArray.length / 255;
                
                // Ses çubuğu güncelle
                const pct = Math.min(avg * 400, 100);
                bar.style.width = pct + '%';
                
                // Eşik kontrolü
                if (avg > this.volumeThreshold && this.onMicTrigger) {{
                    const t = performance.now();
                    this.onMicTrigger(t);
                    this.onMicTrigger = null; // tek seferlik
                }}
                
                this._monitorRAF = requestAnimationFrame(monitor);
            }};
            monitor();
        }}
        
        stopMicrophone() {{
            if (this._monitorRAF) cancelAnimationFrame(this._monitorRAF);
            if (this.micStream) {{
                this.micStream.getTracks().forEach(t => t.stop());
            }}
        }}
    }}
    
    const audio = new AudioManager();
    
    // ═══════════════════════════════════════════
    //  GO/NO-GO MOTOR
    // ═══════════════════════════════════════════
    const CONFIG = {{
        mode: '{mode}',
        targetHits: {target_hits},
        goRatio: {go_ratio},
        minJitter: {min_jitter},
        maxJitter: {max_jitter},
        responseTimeout: {response_timeout},
        soundEnabled: {'true' if sound_enabled else 'false'}
    }};
    
    let state = 'IDLE';
    let trials = [];
    let trialNum = 0;
    let hitCount = 0;
    let stimulusOnsetTime = 0;
    let responseRecorded = false;
    let currentTrialType = 'GO';
    let chronoRAF = null;
    let chronoStart = 0;
    
    // ── Deneme Sırası Üret ──
    function generateTrialSequence(n, goRatio) {{
        let seq = [];
        let consecutiveGo = 0;
        let consecutiveNogo = 0;
        
        for (let i = 0; i < n; i++) {{
            let type;
            if (consecutiveGo >= 3) {{
                type = 'NOGO';
            }} else if (consecutiveNogo >= 3) {{
                type = 'GO';
            }} else {{
                type = Math.random() < goRatio ? 'GO' : 'NOGO';
            }}
            
            if (type === 'GO') {{ consecutiveGo++; consecutiveNogo = 0; }}
            else {{ consecutiveNogo++; consecutiveGo = 0; }}
            
            seq.push(type);
        }}
        return seq;
    }}
    
    // Tahmini deneme sayısı (hedef hit'e ulaşmak için)
    const estimatedTrials = Math.ceil(CONFIG.targetHits / CONFIG.goRatio) + 10;
    let trialSequence = generateTrialSequence(estimatedTrials, CONFIG.goRatio);
    
    // ── UI Elementleri ──
    const $startScreen = document.getElementById('start-screen');
    const $trialScreen = document.getElementById('trial-screen');
    const $endScreen = document.getElementById('end-screen');
    const $phaseText = document.getElementById('phase-text');
    const $subText = document.getElementById('sub-text');
    const $chrono = document.getElementById('chrono');
    const $trialNum = document.getElementById('trial-num');
    const $hitCount = document.getElementById('hit-count');
    const $progressFill = document.getElementById('progress-fill');
    
    // ── Kronometre ──
    function startChrono() {{
        chronoStart = performance.now();
        $chrono.classList.add('visible');
        $chrono.style.color = '#00FF88';
        
        function tick() {{
            const elapsed = performance.now() - chronoStart;
            const seconds = (elapsed / 1000).toFixed(3);
            $chrono.textContent = seconds;
            chronoRAF = requestAnimationFrame(tick);
        }}
        tick();
    }}
    
    function stopChrono() {{
        if (chronoRAF) cancelAnimationFrame(chronoRAF);
        const elapsed = performance.now() - chronoStart;
        $chrono.textContent = (elapsed / 1000).toFixed(3);
        return elapsed;
    }}
    
    function resetChrono() {{
        if (chronoRAF) cancelAnimationFrame(chronoRAF);
        $chrono.textContent = '0.000';
        $chrono.classList.remove('visible');
    }}
    
    // ── Başlat ──
    async function startTest() {{
        audio.init();
        await audio.initMicrophone();
        
        $startScreen.style.display = 'none';
        $trialScreen.style.display = 'flex';
        
        document.getElementById('app').focus();
        
        runNextTrial();
    }}
    
    // ── Deneme Akışı ──
    function runNextTrial() {{
        if (hitCount >= CONFIG.targetHits) {{
            endTest();
            return;
        }}
        
        // Yeni deneme için sıradaki tipi al
        if (trialNum >= trialSequence.length) {{
            trialSequence = trialSequence.concat(generateTrialSequence(20, CONFIG.goRatio));
        }}
        
        currentTrialType = trialSequence[trialNum];
        trialNum++;
        responseRecorded = false;
        
        $trialNum.textContent = trialNum;
        $progressFill.style.width = (hitCount / CONFIG.targetHits * 100) + '%';
        
        // Faz 1: EN GARDE
        setState('EN_GARDE');
    }}
    
    function setState(newState) {{
        state = newState;
        
        switch(newState) {{
            case 'EN_GARDE':
                $trialScreen.style.background = '#0a0a0f';
                $phaseText.textContent = '⚔️ EN GARDE';
                $phaseText.style.color = '#fff';
                $subText.textContent = 'Gardını al...';
                resetChrono();
                if (CONFIG.soundEnabled) audio.playEnGarde();
                
                setTimeout(() => setState('PRETS'), 1500);
                break;
                
            case 'PRETS':
                $phaseText.textContent = '🟡 PRÊTS';
                $phaseText.style.color = '#FFC107';
                $subText.textContent = 'Hazır ol...';
                $trialScreen.style.background = 'radial-gradient(circle, rgba(255,193,7,0.05), #0a0a0f 70%)';
                if (CONFIG.soundEnabled) audio.playPrets();
                
                setTimeout(() => setState('JITTER'), 1000);
                break;
                
            case 'JITTER':
                $phaseText.textContent = '+';
                $phaseText.style.color = '#333';
                $subText.textContent = '';
                $trialScreen.style.background = '#0a0a0f';
                
                // Jitter fazında basış = ERKEN HAMLE
                state = 'JITTER';
                
                const jitter = CONFIG.minJitter + Math.random() * (CONFIG.maxJitter - CONFIG.minJitter);
                setTimeout(() => {{
                    if (state === 'JITTER') setState('STIMULUS');
                }}, jitter);
                break;
                
            case 'STIMULUS':
                responseRecorded = false;
                
                requestAnimationFrame(() => {{
                    if (currentTrialType === 'GO') {{
                        // ── GO: ALLEZ! ──
                        $trialScreen.style.background = 'radial-gradient(circle, rgba(0,255,136,0.3), #0a0a0f 70%)';
                        $phaseText.textContent = '🟢 ALLEZ!';
                        $phaseText.style.color = '#00FF88';
                        $subText.textContent = 'VUR! (Ses veya Tuş)';
                        if (CONFIG.soundEnabled) audio.playAllez();
                        
                        // Kronometre başlat
                        startChrono();
                        stimulusOnsetTime = performance.now();
                        
                        // Mikrofon tetikleyicisi ayarla
                        if (audio.micEnabled) {{
                            audio.onMicTrigger = (t) => {{
                                if (state === 'STIMULUS' && !responseRecorded) {{
                                    handleResponse(t, 'MIC');
                                }}
                            }};
                        }}
                        
                    }} else {{
                        // ── NO-GO: DUR! ──
                        $trialScreen.style.background = 'radial-gradient(circle, rgba(255,23,68,0.3), #0a0a0f 70%)';
                        $phaseText.textContent = '🔴 DUR!';
                        $phaseText.style.color = '#FF1744';
                        $subText.textContent = 'BASMA! Bekle!';
                        if (CONFIG.soundEnabled) audio.playHalt();
                        
                        stimulusOnsetTime = performance.now();
                        
                        // Mikrofon NO-GO'da da dinle (false alarm algılama)
                        if (audio.micEnabled) {{
                            audio.onMicTrigger = (t) => {{
                                if (state === 'STIMULUS' && !responseRecorded) {{
                                    handleResponse(t, 'MIC');
                                }}
                            }};
                        }}
                    }}
                    
                    state = 'STIMULUS';
                    
                    // Timeout
                    setTimeout(() => {{
                        if (state === 'STIMULUS' && !responseRecorded) {{
                            handleTimeout();
                        }}
                    }}, CONFIG.responseTimeout);
                }});
                break;
        }}
    }}
    
    // ── Yanıt İşle ──
    function handleResponse(pressTime, source) {{
        if (responseRecorded) return;
        responseRecorded = true;
        audio.onMicTrigger = null;
        
        const rt = pressTime - stimulusOnsetTime;
        const rtStopped = stopChrono();
        
        let outcome;
        if (state === 'JITTER') {{
            // Erken hamle!
            outcome = 'PREMATURE';
            showFeedback('⚠️ ERKEN HAMLE!', '#FF9100', 'Bekleme fazında bastın');
            if (CONFIG.soundEnabled) audio.playError();
        }} else if (currentTrialType === 'GO') {{
            if (rt < 80) {{
                outcome = 'PREMATURE';
                showFeedback('⚠️ ÇOK ERKEN!', '#FF9100', 'Tahmin ettin, reaksiyon değil');
                if (CONFIG.soundEnabled) audio.playError();
            }} else {{
                outcome = 'HIT';
                hitCount++;
                $hitCount.textContent = hitCount;
                $chrono.style.color = '#00FF88';
                showFeedback('✅ İSABET!', '#00FF88', rt.toFixed(1) + ' ms (' + source + ')');
                if (CONFIG.soundEnabled) audio.playSuccess();
            }}
        }} else {{
            // NO-GO'da bastı
            outcome = 'FALSE_ALARM';
            showFeedback('❌ DÜRTÜ HATASI!', '#FF1744', 'DUR sinyalinde bastın');
            if (CONFIG.soundEnabled) audio.playError();
        }}
        
        trials.push({{
            trial_number: trialNum,
            trial_type: currentTrialType,
            responded: true,
            reaction_time_ms: state === 'JITTER' ? null : parseFloat(rt.toFixed(2)),
            outcome: outcome,
            source: source,
            timestamp: Date.now()
        }});
        
        setTimeout(runNextTrial, 1500);
    }}
    
    function handleTimeout() {{
        responseRecorded = true;
        audio.onMicTrigger = null;
        
        let outcome;
        if (currentTrialType === 'GO') {{
            outcome = 'OMISSION_ERROR';
            resetChrono();
            showFeedback('⏰ KAÇIRDIN!', '#FF9100', 'Süre doldu, vuruş yok');
            if (CONFIG.soundEnabled) audio.playError();
        }} else {{
            outcome = 'CORRECT_REJECTION';
            showFeedback('✅ DOĞRU BEKLEDİN', '#448AFF', 'DUR sinyalinde sabrettin');
            if (CONFIG.soundEnabled) audio.playSuccess();
        }}
        
        trials.push({{
            trial_number: trialNum,
            trial_type: currentTrialType,
            responded: false,
            reaction_time_ms: null,
            outcome: outcome,
            source: null,
            timestamp: Date.now()
        }});
        
        setTimeout(runNextTrial, 1500);
    }}
    
    function showFeedback(text, color, detail) {{
        state = 'FEEDBACK';
        $phaseText.textContent = text;
        $phaseText.style.color = color;
        $subText.textContent = detail;
        $trialScreen.style.background = '#0a0a0f';
    }}
    
    // ── Test Bitişi ──
    function endTest() {{
        state = 'DONE';
        audio.onMicTrigger = null;
        audio.stopMicrophone();
        resetChrono();
        
        $trialScreen.style.display = 'none';
        $endScreen.style.display = 'block';
        
        // Özet hesapla
        const hits = trials.filter(t => t.outcome === 'HIT');
        const nogoTrials = trials.filter(t => t.trial_type === 'NOGO');
        const correctRej = trials.filter(t => t.outcome === 'CORRECT_REJECTION');
        
        const meanRT = hits.length > 0 ? (hits.reduce((s, t) => s + t.reaction_time_ms, 0) / hits.length).toFixed(0) : '-';
        const impulseRate = nogoTrials.length > 0 ? ((correctRej.length / nogoTrials.length) * 100).toFixed(0) : '-';
        
        document.getElementById('sum-rt').textContent = meanRT + (meanRT !== '-' ? ' ms' : '');
        document.getElementById('sum-hits').textContent = hits.length + ' / ' + CONFIG.targetHits;
        document.getElementById('sum-impulse').textContent = impulseRate + (impulseRate !== '-' ? '%' : '');
        
        // Streamlit'e gönder
        Bridge.sendData({{
            status: 'COMPLETE',
            mode: CONFIG.mode,
            completed_at: Date.now(),
            total_hits: hitCount,
            trials: trials
        }});
    }}
    
    // ── Klavye Dinleyici ──
    document.addEventListener('keydown', (e) => {{
        if (e.code !== 'Space' && e.code !== 'Enter') return;
        e.preventDefault();
        if (e.repeat) return;
        
        const t = performance.now();
        
        if (state === 'JITTER') {{
            handleResponse(t, 'KEY');
        }} else if (state === 'STIMULUS' && !responseRecorded) {{
            handleResponse(t, 'KEY');
        }}
    }}, {{ passive: false, capture: true }});
    
    // İlk focus
    document.getElementById('app').setAttribute('tabindex', '0');
    document.getElementById('app').focus();
    </script>
    </body>
    </html>
    """
    
    import streamlit.components.v1 as components
    
    result = components.html(component_html, height=720, scrolling=False)
    
    # Sonuç geldiğinde kaydet (postMessage ile)
    # Not: components.html doğrudan setComponentValue desteklemez,
    # ama biz window.parent.postMessage ile veri gönderiyoruz
    # Streamlit rerun döngüsünde session_state'e kaydedilir


# ═══════════════════════════════════════════════════════════════
#  SAYFA: SONUÇLAR (Dashboard)
# ═══════════════════════════════════════════════════════════════
elif page == "📊 Sonuçlar":
    st.markdown("""<div style='text-align: center; margin-bottom: 2rem;'>
        <h1 style='font-size: 2rem;'>📊 Sonuç Analizi</h1>
        <p style='color: #666;'>Test tamamlandıktan sonra detaylı metrikler burada görünür</p>
    </div>""", unsafe_allow_html=True)
    
    # Demo veri veya gerçek veri
    if not st.session_state.test_history:
        st.info("📋 Henüz test sonucu yok. Antrenman sayfasından bir test tamamlayın.")
        
        st.markdown("---")
        st.markdown("### 🧪 Demo Verisi ile Önizleme")
        
        if st.button("Demo Sonuçlar Oluştur", use_container_width=True):
            np.random.seed(42)
            demo_trials = []
            for i in range(20):
                trial_type = np.random.choice(["GO", "NOGO"], p=[0.7, 0.3])
                if trial_type == "GO":
                    rt = np.random.normal(280, 50)
                    rt = max(120, min(800, rt))
                    outcome = "HIT" if np.random.random() > 0.1 else "OMISSION_ERROR"
                    demo_trials.append({
                        "trial_number": i+1,
                        "trial_type": trial_type,
                        "responded": outcome == "HIT",
                        "reaction_time_ms": round(rt, 2) if outcome == "HIT" else None,
                        "outcome": outcome,
                        "source": "KEY"
                    })
                else:
                    outcome = "CORRECT_REJECTION" if np.random.random() > 0.2 else "FALSE_ALARM"
                    demo_trials.append({
                        "trial_number": i+1,
                        "trial_type": trial_type,
                        "responded": outcome == "FALSE_ALARM",
                        "reaction_time_ms": round(np.random.normal(350, 80), 2) if outcome == "FALSE_ALARM" else None,
                        "outcome": outcome,
                        "source": "KEY" if outcome == "FALSE_ALARM" else None
                    })
            
            st.session_state.test_history.append({
                "mode": st.session_state.test_mode,
                "athlete_name": st.session_state.athlete_name or "Demo Sporcu",
                "date": datetime.datetime.now().isoformat(),
                "trials": demo_trials
            })
            st.rerun()
    
    else:
        # Son test sonuçları
        test_data = st.session_state.test_history[-1]
        df = pd.DataFrame(test_data["trials"])
        
        # ── Metrikler ──
        hit_trials = df[df["outcome"] == "HIT"]
        nogo_trials = df[df["trial_type"] == "NOGO"]
        correct_rej = df[df["outcome"] == "CORRECT_REJECTION"]
        false_alarms = df[df["outcome"] == "FALSE_ALARM"]
        
        mean_rt = hit_trials["reaction_time_ms"].mean() if len(hit_trials) > 0 else 0
        std_rt = hit_trials["reaction_time_ms"].std() if len(hit_trials) > 1 else 0
        min_rt = hit_trials["reaction_time_ms"].min() if len(hit_trials) > 0 else 0
        max_rt = hit_trials["reaction_time_ms"].max() if len(hit_trials) > 0 else 0
        impulse_rate = (len(correct_rej) / len(nogo_trials) * 100) if len(nogo_trials) > 0 else 0
        go_trials = df[df["trial_type"] == "GO"]
        hit_rate = (len(hit_trials) / len(go_trials) * 100) if len(go_trials) > 0 else 0
        
        st.markdown(f"""<div style='text-align: center; margin-bottom: 1.5rem; color: #888;'>
            🤺 {test_data.get('athlete_name', '-')} • 
            {test_data.get('date', '-')[:10]}
        </div>""", unsafe_allow_html=True)
        
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Ort. RT", f"{mean_rt:.0f} ms")
        c2.metric("En Hızlı", f"{min_rt:.0f} ms")
        c3.metric("En Yavaş", f"{max_rt:.0f} ms")
        c4.metric("Std Sapma", f"{std_rt:.0f} ms")
        c5.metric("Dürtü Kontrol", f"{impulse_rate:.0f}%")
        c6.metric("İsabet Oranı", f"{hit_rate:.0f}%")
        
        st.markdown("---")
        
        # ── Grafikler ──
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Bilişsel Yorgunluk Eğrisi
            if len(hit_trials) > 0:
                fig1 = go.Figure()
                fig1.add_trace(go.Scatter(
                    x=hit_trials["trial_number"],
                    y=hit_trials["reaction_time_ms"],
                    mode='lines+markers',
                    marker=dict(size=10, color='#00FF88', line=dict(width=1, color='#005533')),
                    line=dict(width=2, color='#00FF88'),
                    name='RT (ms)'
                ))
                
                # Trend çizgisi
                if len(hit_trials) > 2:
                    z = np.polyfit(hit_trials["trial_number"], hit_trials["reaction_time_ms"], 1)
                    p = np.poly1d(z)
                    x_trend = np.linspace(hit_trials["trial_number"].min(), hit_trials["trial_number"].max(), 50)
                    fig1.add_trace(go.Scatter(
                        x=x_trend,
                        y=p(x_trend),
                        mode='lines',
                        line=dict(width=2, color='#FF9100', dash='dash'),
                        name='Trend'
                    ))
                
                fig1.update_layout(
                    title="⏱️ Bilişsel Yorgunluk Eğrisi",
                    xaxis_title="Deneme No",
                    yaxis_title="Reaksiyon Süresi (ms)",
                    template="plotly_dark",
                    height=400,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(10,10,15,0.8)',
                    font=dict(family="Inter"),
                    margin=dict(l=40, r=20, t=50, b=40)
                )
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("İsabet verisi yok")
        
        with chart_col2:
            # Yanıt Dağılımı
            outcome_counts = df["outcome"].value_counts()
            colors_map = {
                "HIT": "#00FF88",
                "CORRECT_REJECTION": "#448AFF",
                "FALSE_ALARM": "#FF1744",
                "OMISSION_ERROR": "#FF9100",
                "PREMATURE": "#AA00FF"
            }
            labels_map = {
                "HIT": "İsabet",
                "CORRECT_REJECTION": "Doğru Bekleme",
                "FALSE_ALARM": "Dürtü Hatası",
                "OMISSION_ERROR": "Kaçırma",
                "PREMATURE": "Erken Hamle"
            }
            
            fig2 = go.Figure(data=[go.Pie(
                labels=[labels_map.get(k, k) for k in outcome_counts.index],
                values=outcome_counts.values,
                hole=0.45,
                marker=dict(colors=[colors_map.get(k, '#888') for k in outcome_counts.index]),
                textfont=dict(size=13),
                textinfo='label+percent'
            )])
            fig2.update_layout(
                title="📊 Yanıt Dağılımı",
                template="plotly_dark",
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(10,10,15,0.8)',
                font=dict(family="Inter"),
                margin=dict(l=20, r=20, t=50, b=20),
                showlegend=False
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # ── RT Histogram ──
        if len(hit_trials) > 0:
            fig3 = go.Figure()
            fig3.add_trace(go.Histogram(
                x=hit_trials["reaction_time_ms"],
                nbinsx=12,
                marker_color='#00FF88',
                opacity=0.75,
                name='RT'
            ))
            fig3.update_layout(
                title="📈 Reaksiyon Süresi Dağılımı",
                xaxis_title="Reaksiyon Süresi (ms)",
                yaxis_title="Frekans",
                template="plotly_dark",
                height=350,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(10,10,15,0.8)',
                font=dict(family="Inter"),
                margin=dict(l=40, r=20, t=50, b=40)
            )
            st.plotly_chart(fig3, use_container_width=True)
        
        # ── Detay Tablosu ──
        st.markdown("### 📋 Detaylı Deneme Verileri")
        
        display_df = df.copy()
        col_rename = {
            "trial_number": "Deneme No",
            "trial_type": "Uyaran Tipi",
            "responded": "Yanıt Verdi",
            "reaction_time_ms": "RT (ms)",
            "outcome": "Sonuç",
            "source": "Kaynak"
        }
        display_df = display_df.rename(columns=col_rename)
        outcome_tr = {
            "HIT": "✅ İsabet",
            "CORRECT_REJECTION": "✅ Doğru Bekleme",
            "FALSE_ALARM": "❌ Dürtü Hatası",
            "OMISSION_ERROR": "⏰ Kaçırma",
            "PREMATURE": "⚠️ Erken Hamle"
        }
        display_df["Sonuç"] = display_df["Sonuç"].map(lambda x: outcome_tr.get(x, x))
        display_df["Yanıt Verdi"] = display_df["Yanıt Verdi"].map({True: "Evet", False: "Hayır"})
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # ── İndirme ──
        st.markdown("### 💾 Veri İndirme")
        dl1, dl2 = st.columns(2)
        
        with dl1:
            csv_data = df.to_csv(index=False).encode('utf-8')
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            athlete = st.session_state.athlete_name or "sporcu"
            st.download_button(
                "📥 CSV İndir",
                data=csv_data,
                file_name=f"kilicRT_{athlete}_{ts}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with dl2:
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Ham Veri', index=False)
                
                metrics_data = {
                    "Metrik": ["Ortalama RT (ms)", "En Hızlı RT (ms)", "En Yavaş RT (ms)", 
                              "Std Sapma (ms)", "Dürtü Kontrolü (%)", "İsabet Oranı (%)"],
                    "Değer": [f"{mean_rt:.1f}", f"{min_rt:.1f}", f"{max_rt:.1f}",
                             f"{std_rt:.1f}", f"{impulse_rate:.1f}", f"{hit_rate:.1f}"]
                }
                pd.DataFrame(metrics_data).to_excel(writer, sheet_name='Özet', index=False)
                
                info_data = {
                    "Bilgi": ["Sporcu", "Branş", "Tarih", "Mod"],
                    "Değer": [athlete, "Kılıç (Sabre)", ts[:8], test_data.get("mode", "-")]
                }
                pd.DataFrame(info_data).to_excel(writer, sheet_name='Sporcu Bilgisi', index=False)
            
            st.download_button(
                "📊 Excel İndir",
                data=buffer.getvalue(),
                file_name=f"kilicRT_{athlete}_{ts}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )


# ═══════════════════════════════════════════════════════════════
#  SAYFA: AYARLAR
# ═══════════════════════════════════════════════════════════════
elif page == "⚙️ Ayarlar":
    st.markdown("""<div style='text-align: center; margin-bottom: 2rem;'>
        <h1 style='font-size: 2rem;'>⚙️ Serbest Atölye Ayarları</h1>
        <p style='color: #666;'>Antrenör kontrolünde özelleştirilebilir parametreler</p>
    </div>""", unsafe_allow_html=True)
    
    settings = st.session_state.custom_settings
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎯 Test Parametreleri")
        
        go_ratio = st.slider(
            "Go/No-Go Oranı (% Go)", 
            min_value=50, max_value=95, 
            value=settings["go_ratio"],
            help="Go uyaranlarının yüzdesi. Örn: 70 = %70 Go, %30 No-Go"
        )
        
        target_hits = st.number_input(
            "Hedef Deneme Sayısı",
            min_value=5, max_value=50,
            value=settings["target_hits"],
            help="Toplam deneme sayısı (Serbest modda)"
        )
        
        response_timeout = st.number_input(
            "Yanıt Zaman Aşımı (ms)",
            min_value=500, max_value=2000, step=100,
            value=settings["response_timeout"],
            help="Uyaran sonrası maksimum bekleme süresi"
        )
    
    with col2:
        st.markdown("### ⏱️ Zamanlama")
        
        min_jitter = st.number_input(
            "Minimum Bekleme Süresi (ms)",
            min_value=500, max_value=3000, step=100,
            value=settings["min_jitter"],
            help="PRÊTS sonrası minimum rastgele bekleme"
        )
        
        max_jitter = st.number_input(
            "Maksimum Bekleme Süresi (ms)",
            min_value=2000, max_value=6000, step=100,
            value=settings["max_jitter"],
            help="PRÊTS sonrası maksimum rastgele bekleme"
        )
        
        sound_enabled = st.toggle("🔊 Ses Efektleri", value=st.session_state.sound_enabled)
    
    st.markdown("---")
    
    save_col, reset_col = st.columns(2)
    
    with save_col:
        if st.button("💾 Ayarları Kaydet", use_container_width=True, type="primary"):
            st.session_state.custom_settings = {
                "go_ratio": go_ratio,
                "min_jitter": min_jitter,
                "max_jitter": max_jitter,
                "target_hits": target_hits,
                "response_timeout": response_timeout,
            }
            st.session_state.sound_enabled = sound_enabled
            st.success("✅ Ayarlar kaydedildi!")
    
    with reset_col:
        if st.button("🔄 Varsayılana Sıfırla", use_container_width=True):
            st.session_state.custom_settings = {
                "go_ratio": 70,
                "min_jitter": 1500,
                "max_jitter": 4500,
                "target_hits": 20,
                "response_timeout": 1000,
            }
            st.session_state.sound_enabled = True
            st.success("🔄 Varsayılan ayarlara döndürüldü!")
            st.rerun()
    
    # Tahmini süre hesapla
    avg_jitter = (min_jitter + max_jitter) / 2
    avg_trial_time = 1500 + 1000 + avg_jitter + response_timeout + 1500  # en garde + prets + jitter + response + feedback
    estimated_total = target_hits * avg_trial_time / 1000 / 60
    
    st.markdown(f"""<div class='glass-card' style='text-align: center; margin-top: 1rem;'>
        <p style='color: #888; font-size: 0.8rem;'>TAHMİNİ TEST SÜRESİ</p>
        <p style='font-family: JetBrains Mono; font-size: 2rem; color: #00FF88;'>{estimated_total:.1f} dk</p>
        <p style='color: #555; font-size: 0.75rem;'>Ortalama deneme süresi: {avg_trial_time/1000:.1f} sn</p>
    </div>""", unsafe_allow_html=True)
