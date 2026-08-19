import streamlit as st
import os
import datetime
import pandas as pd
import numpy as np
import plotly.graph_objects as go

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
    
    st.markdown("### 🎤 Hassasiyet (Ses Eşiği)")
    st.caption("Komutların algılanması için gereken ses seviyesi.")
    threshold = st.slider("Ses Eşiği", 0.01, 0.50, 0.02, 0.01,
                          help="Fısıldayarak bile konuşsanız algılaması için 0.02'ye ayarlandı")
    st.divider()
    if st.session_state.results:
        if st.button("🗑️ Temizle", use_container_width=True):
            st.session_state.results = []
            st.rerun()

st.markdown("""<div style='text-align:center; padding: 0.3rem 0 0.8rem;'>
    <h1 style='font-size: 2rem; margin:0;'>⚔️ Kılıç Reaksiyon Kronometresi</h1>
    <p style='color: #666; font-size: 0.85rem;'>Saf Ses Şiddeti Sistemi (Yapay Zekasız, %100 Uyumlu)</p>
</div>""", unsafe_allow_html=True)

component_html = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap');
    *{{margin:0;padding:0;box-sizing:border-box;}}
    body{{font-family:'Inter',sans-serif;background:#0a0a0f;color:#fff;overflow:hidden;user-select:none;}}
    #app{{width:100%;height:660px;display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative;outline:none;}}

    #phase{{font-size:5.5rem;font-weight:900;text-align:center;line-height:1;transition:color 0.1s,text-shadow 0.15s;color:#333;}}
    #phase.engarde{{color:#fff;text-shadow:0 0 40px rgba(255,255,255,0.25);}}
    #phase.prets{{color:#FFC107;text-shadow:0 0 50px rgba(255,193,7,0.35);}}
    #phase.allez{{color:#00FF88;text-shadow:0 0 80px rgba(0,255,136,0.5);}}
    #phase.stopped{{color:#00AAFF;text-shadow:0 0 40px rgba(0,170,255,0.3);}}

    #status{{font-size:1.1rem;font-weight:600;color:#888;margin-top:1rem;letter-spacing:0.05em;}}

    #chrono{{font-family:'JetBrains Mono',monospace;font-size:5.5rem;font-weight:700;color:#222;margin-top:0.8rem;transition:color 0.1s,text-shadow 0.15s;}}
    #chrono.running{{color:#00FF88;text-shadow:0 0 60px rgba(0,255,136,0.35);}}
    #chrono.stopped{{color:#00AAFF;text-shadow:0 0 30px rgba(0,170,255,0.2);}}

    #unit{{font-size:0.85rem;color:#444;margin-top:0.2rem;font-family:'JetBrains Mono',monospace;}}

    #last-result{{margin-top:1rem;font-size:1rem;color:#555;min-height:1.5rem;}}
    #last-result .rt{{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:1.4rem;color:#00FF88;}}

    /* SES BAR STİLLERİ */
    #mic-sec{{margin-top:1.5rem;text-align:center;width:400px;}}
    #mic-lbl{{font-size:0.75rem;color:#666;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.4rem;display:flex;justify-content:space-between;}}
    #mic-bg{{width:100%;height:20px;background:rgba(26,31,46,0.8);border-radius:10px;position:relative;overflow:hidden;border:1px solid rgba(255,255,255,0.1);}}
    #mic-fill{{height:100%;width:0%;border-radius:10px;background:linear-gradient(90deg,#00AAFF,#00FF88);transition:width 0.05s linear;}}
    
    /* Eşik Çizgisi */
    #threshold-line{{position:absolute;top:0;bottom:0;width:2px;background:red;z-index:2;box-shadow:0 0 5px red;}}

    #steps{{position:absolute;top:1.2rem;left:50%;transform:translateX(-50%);display:flex;gap:0.4rem;align-items:center;}}
    .step{{padding:0.35rem 1rem;border-radius:8px;font-size:0.8rem;font-weight:700;
        background:rgba(26,31,46,0.6);border:2px solid #222;color:#444;transition:all 0.15s;letter-spacing:0.05em;}}
    .step.waiting{{border-color:#FFC107;color:#FFC107;animation:blink 1.2s ease-in-out infinite;}}
    .step.done{{border-color:#00FF88;color:#00FF88;background:rgba(0,255,136,0.1);animation:none;}}
    .step.ready{{border-color:#00FF88;color:#00FF88;animation:blink 0.6s ease-in-out infinite;}}
    .step-arrow{{color:#333;font-size:0.9rem;}}
    @keyframes blink{{0%,100%{{opacity:1;}}50%{{opacity:0.3;}}}}

    #counter{{position:absolute;top:1rem;right:1.5rem;font-family:'JetBrains Mono',monospace;font-size:0.85rem;color:#333;
        background:rgba(26,31,46,0.6);padding:0.4rem 0.8rem;border-radius:8px;border:1px solid rgba(255,255,255,0.04);}}

    #instruction{{position:absolute;bottom:1.5rem;font-size:0.8rem;color:#444;text-align:center;line-height:1.6;}}
    #instruction strong{{color:#777;}}

    #start-btn{{padding:1.2rem 3rem;font-size:1.2rem;font-weight:700;font-family:'Inter',sans-serif;
        background:linear-gradient(135deg,#00FF88,#00CC6A);color:#000;border:none;border-radius:16px;cursor:pointer;animation:pulse 2s ease-in-out infinite;}}
    #start-btn:hover{{transform:scale(1.05);box-shadow:0 0 40px rgba(0,255,136,0.3);}}

    #mic-selector-container {{ margin-bottom: 1.5rem; }}
    #mic-select {{ padding: 0.6rem; border-radius: 8px; background: #222; color: #fff; border: 1px solid #444; font-family: 'Inter', sans-serif; font-size: 0.9rem; min-width: 250px; }}

    #flash{{position:absolute;top:0;left:0;right:0;bottom:0;pointer-events:none;opacity:0;transition:opacity 0.1s;}}
    .hidden{{display:none !important;}}
    @keyframes pulse{{0%,100%{{transform:scale(1);}}50%{{transform:scale(1.03);}}}}
</style>
</head>
<body>
<div id="app" tabindex="0">
    <div id="flash"></div>

    <div id="intro">
        <div style="font-size:3.5rem;margin-bottom:1rem;">🎙️⚡</div>
        <p style="color:#ccc;margin-bottom:0.5rem;font-size:1.1rem;font-weight:600;">Ritmik Ses Sistemi</p>
        <p style="color:#888;margin-bottom:1.5rem;max-width:420px;text-align:center;line-height:1.6;font-size:0.9rem;">
            Antrenörün "Angart", "Hazır" ve "Başlayın" komutları arasında en az <strong>Yarım Saniye (0.5 sn)</strong> beklemesi yeterlidir.<br><br>
            <i>Not: Eğer sistem sesinizi hiç algılamıyorsa, aşağıdan doğru mikrofonu seçtiğinize emin olun.</i>
        </p>
        
        <div id="mic-selector-container">
            <select id="mic-select">
                <option value="">🎤 Varsayılan Mikrofon (İzin İsteniyor...)</option>
            </select>
        </div>

        <button id="start-btn" onclick="initAudioSync(); startApp();">🎤 BAŞLAT</button>
    </div>

    <div id="main-screen" class="hidden">
        <div id="steps">
            <div class="step waiting" id="s1">ANGART</div>
            <div class="step-arrow">→</div>
            <div class="step" id="s2">HAZIR</div>
            <div class="step-arrow">→</div>
            <div class="step" id="s3">BAŞLAYIN!</div>
        </div>
        <div id="counter">Ölçüm: <span id="cnt">0</span></div>

        <div id="phase">⚔️</div>
        <div id="status">🎤 İlk komut için ses bekleniyor...</div>
        
        <div id="chrono">0.000</div>
        <div id="unit">saniye</div>
        <div id="last-result"></div>

        <div id="mic-sec">
            <div id="mic-lbl">
                <span>Ses Seviyesi (Konuştukça dolar)</span>
                <span id="vol-text" style="font-family:monospace; color:#aaa;">0.00</span>
            </div>
            <div id="mic-bg">
                <div id="threshold-line" style="left: {threshold * 100}%"></div>
                <div id="mic-fill"></div>
            </div>
        </div>

        <div id="instruction">
            Komutlar arasında en az 0.5 sn bekleyin | Ölçümü durdurmak için <strong>SPACE</strong>
        </div>
    </div>
</div>

<script>
    const TH = {threshold};
    let audioCtx=null, analyser=null, micStream=null;
    
    // State Machine
    let currentStep=0; 
    let isRunning=false; 
    let startTime=0; 
    let chronoRAF=null;
    let measureCount=0; 
    let allResults=[];
    
    // Cooldown mekanizması
    let isCooldown = false;
    const COOLDOWN_MS = 500; // Komutlar arası zorunlu bekleme süresi (Yarım saniye)

    const $intro=document.getElementById('intro'), $main=document.getElementById('main-screen');
    const $phase=document.getElementById('phase'), $status=document.getElementById('status');
    const $chrono=document.getElementById('chrono');
    const $lastResult=document.getElementById('last-result'), $cnt=document.getElementById('cnt');
    const $flash=document.getElementById('flash'), $app=document.getElementById('app');
    const $s1=document.getElementById('s1'), $s2=document.getElementById('s2'), $s3=document.getElementById('s3');
    const $micFill=document.getElementById('mic-fill'), $volText=document.getElementById('vol-text');
    const $micSelect=document.getElementById('mic-select');

    // Mikrofonları Listeleme
    async function populateMics() {{
        try {{
            // İzin istemek için kısa bir stream alıp kapatıyoruz
            const tempStream = await navigator.mediaDevices.getUserMedia({{audio: true}});
            tempStream.getTracks().forEach(track => track.stop());
            
            const devices = await navigator.mediaDevices.enumerateDevices();
            const audioInputs = devices.filter(device => device.kind === 'audioinput');
            
            $micSelect.innerHTML = '';
            if(audioInputs.length === 0) {{
                $micSelect.innerHTML = '<option value="">Mikrofon Bulunamadı!</option>';
            }} else {{
                audioInputs.forEach((device, index) => {{
                    const option = document.createElement('option');
                    option.value = device.deviceId;
                    option.text = device.label || `Mikrofon ${{index + 1}}`;
                    $micSelect.appendChild(option);
                }});
            }}
        }} catch(e) {{
            console.warn("Mikrofon listesi alınamadı:", e);
            $micSelect.innerHTML = '<option value="">Mikrofon izinleri reddedildi veya cihaz yok.</option>';
        }}
    }}

    // Sayfa yüklendiğinde mikrofonları getir
    window.addEventListener('load', populateMics);

    // Senkron başlatma (Tarayıcıların mikrofonu sessize almasını engeller)
    function initAudioSync() {{
        const AC = window.AudioContext || window.webkitAudioContext;
        if(!audioCtx) audioCtx = new AC();
        if(audioCtx.state === 'suspended') audioCtx.resume();
    }}

    async function startApp() {{
        initAudioSync();

        const deviceId = $micSelect.value;
        const constraints = deviceId ? {{ audio: {{ deviceId: {{ exact: deviceId }} }} }} : {{ audio: true }};

        try {{
            micStream = await navigator.mediaDevices.getUserMedia(constraints);
        }} catch(e) {{
            alert('Mikrofon erişimi reddedildi veya seçili mikrofon kullanılamıyor! Lütfen izin verdiğinizden emin olun.');
            return;
        }}

        const source = audioCtx.createMediaStreamSource(micStream);
        analyser = audioCtx.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);

        $intro.classList.add('hidden');
        $main.classList.remove('hidden');
        $app.focus();
        
        resetAll();
        audioLoop(); // Mikrofonu sürekli dinle
    }}

    function audioLoop() {{
        const buf = new Uint8Array(analyser.frequencyBinCount);
        
        function tick() {{
            analyser.getByteFrequencyData(buf);
            let maxVal = 0;
            for(let i=0; i<buf.length; i++) {{
                if(buf[i] > maxVal) maxVal = buf[i];
            }}
            const avg = maxVal / 255;
            
            // UI Güncelleme
            $volText.textContent = avg.toFixed(2);
            $micFill.style.width = Math.min(avg * 100, 100) + '%';
            if(avg > TH) $micFill.style.background = 'linear-gradient(90deg,#FF9100,#FF1744)';
            else $micFill.style.background = 'linear-gradient(90deg,#00AAFF,#00FF88)';

            // Mantık
            if(avg > TH && !isCooldown && !isRunning) {{
                handleLoudSound();
            }}

            requestAnimationFrame(tick);
        }}
        tick();
    }}

    function handleLoudSound() {{
        if(currentStep === 0) {{
            goToStep1();
        }} 
        else if(currentStep === 1) {{
            goToStep2();
        }} 
        else if(currentStep === 2) {{
            goToStep3();
        }}
    }}

    function triggerCooldown() {{
        isCooldown = true;
        setTimeout(() => {{
            isCooldown = false;
            // Cooldown bittiğinde UI'ı güncelleyebiliriz
            if(currentStep === 1) {{
                $status.textContent = '🟢 Bekleme bitti. "Hazır!" diyebilirsiniz.';
                $status.style.color = '#00FF88';
                $s2.className = 'step ready';
            }} else if (currentStep === 2) {{
                $status.textContent = '🟢 Bekleme bitti. "Başlayın!" diyebilirsiniz.';
                $status.style.color = '#00FF88';
                $s3.className = 'step ready';
            }}
        }}, COOLDOWN_MS);
    }}

    function goToStep1() {{
        currentStep = 1;
        $s1.className = 'step done';
        $s2.className = 'step waiting';
        $phase.textContent = '⚔️ ANGART';
        $phase.className = 'engarde';
        $status.textContent = '⏳ ' + (COOLDOWN_MS/1000).toFixed(1) + ' sn bekleme...';
        $status.style.color = '#FF9100';
        doFlash('#ffffff', 0.1);
        triggerCooldown();
    }}

    function goToStep2() {{
        currentStep = 2;
        $s2.className = 'step done';
        $s3.className = 'step waiting';
        $phase.textContent = '🟡 HAZIR';
        $phase.className = 'prets';
        $status.textContent = '⏳ ' + (COOLDOWN_MS/1000).toFixed(1) + ' sn bekleme...';
        $status.style.color = '#FF9100';
        doFlash('#FFC107', 0.15);
        triggerCooldown();
    }}

    function goToStep3() {{
        currentStep = 3;
        isRunning = true;
        startTime = performance.now();

        $s3.className = 'step done';
        $phase.textContent = '🟢 BAŞLAYIN!';
        $phase.className = 'allez';
        $status.textContent = '⏱️ SPACE BAS!';
        $status.style.color = '#00FF88';
        $chrono.className = 'running';
        doFlash('#00FF88', 0.25);

        function chronoTick() {{
            if(!isRunning) return;
            $chrono.textContent = ((performance.now()-startTime)/1000).toFixed(3);
            chronoRAF = requestAnimationFrame(chronoTick);
        }}
        chronoTick();
    }}

    function stopChrono() {{
        if(!isRunning) return;
        const elapsed = performance.now() - startTime;
        isRunning = false;
        if(chronoRAF) cancelAnimationFrame(chronoRAF);

        const sec = (elapsed/1000).toFixed(3);
        const ms = elapsed.toFixed(1);
        $chrono.textContent = sec;
        $chrono.className = 'stopped';
        $phase.textContent = '✅ ' + ms + ' ms';
        $phase.className = 'stopped';
        
        $status.textContent = 'Kaydedildi! 2 sn sonra yeni döngü...';
        $status.style.color = '#00AAFF';
        doFlash('#00AAFF', 0.2);

        measureCount++;
        $cnt.textContent = measureCount;
        $lastResult.innerHTML = 'Son: <span class="rt">' + ms + ' ms</span>';

        allResults.push({{number:measureCount, reaction_time_ms:parseFloat(ms), timestamp:Date.now()}});

        window.parent.postMessage({{
            isStreamlitMessage:true, type:'streamlit:setComponentValue',
            value:{{status:'RESULT', count:measureCount, reaction_time_ms:parseFloat(ms), all_results:allResults}}
        }},'*');

        setTimeout(resetAll, 2000);
    }}

    function resetAll() {{
        currentStep = 0;
        isRunning = false;
        isCooldown = false;
        
        $s1.className = 'step waiting'; 
        $s2.className = 'step'; 
        $s3.className = 'step';
        
        $phase.textContent = '⚔️'; 
        $phase.className = '';
        
        $chrono.textContent = '0.000'; 
        $chrono.className = '';
        
        $status.textContent = '🎤 "Angart" diyebilirsiniz...'; 
        $status.style.color = '#555';
        $lastResult.innerHTML = '';
    }}

    function doFlash(hex,a) {{
        const r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
        $flash.style.background = 'rgba('+r+','+g+','+b+','+a+')';
        $flash.style.opacity = '1';
        setTimeout(() => {{ $flash.style.opacity = '0'; }}, 200);
    }}

    document.addEventListener('keydown', (e) => {{
        if(e.code === 'Space' || e.code === 'Enter') {{ 
            e.preventDefault(); 
            if(!e.repeat && isRunning) stopChrono();
        }}
    }}, {{passive: false, capture: true}});
    
    $app.focus();

    window.parent.postMessage({{isStreamlitMessage:true,type:'streamlit:componentReady',apiVersion:1}},'*');
    window.parent.postMessage({{isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:730}},'*');
</script>
</body>
</html>
"""

import streamlit.components.v1 as components
components.html(component_html, height=730, scrolling=False)

st.markdown("---")
if st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Ölçüm",len(df))
    c2.metric("Ort. RT",f"{df['reaction_time_ms'].mean():.0f} ms")
    c3.metric("En Hızlı",f"{df['reaction_time_ms'].min():.0f} ms")
    c4.metric("En Yavaş",f"{df['reaction_time_ms'].max():.0f} ms")
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=df["number"],y=df["reaction_time_ms"],mode='lines+markers',
        marker=dict(size=10,color='#00FF88'),line=dict(width=2,color='#00FF88')))
    fig.update_layout(title="Reaksiyon Süreleri",xaxis_title="Ölçüm",yaxis_title="ms",
        template="plotly_dark",height=300,paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(10,10,15,0.8)',margin=dict(l=40,r=20,t=50,b=40))
    st.plotly_chart(fig,use_container_width=True)
    csv=df.to_csv(index=False).encode('utf-8')
    ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    athlete=st.session_state.athlete_name or "sporcu"
    st.download_button("📥 CSV İndir",csv,f"kilicRT_{athlete}_{ts}.csv","text/csv",use_container_width=True)
else:
    st.info("👆 Başlat → 1. Angart → (0.5sn bekle) → 2. Hazır → (0.5sn bekle) → 3. Başlayın! ⏱️ → SPACE")
