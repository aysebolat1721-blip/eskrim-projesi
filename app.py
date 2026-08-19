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
    st.divider()
    if st.session_state.results:
        if st.button("🗑️ Sonuçları Temizle", use_container_width=True):
            st.session_state.results = []
            st.rerun()

st.markdown("""<div style='text-align:center; padding: 0.5rem 0 1rem;'>
    <h1 style='font-size: 2rem; margin:0;'>⚔️ Kılıç Reaksiyon Kronometresi</h1>
    <p style='color: #666; font-size: 0.9rem;'>Sesli komut tanıma + Anlık kronometre</p>
</div>""", unsafe_allow_html=True)

component_html = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap');
    *{margin:0;padding:0;box-sizing:border-box;}
    body{font-family:'Inter',sans-serif;background:#0a0a0f;color:#fff;overflow:hidden;user-select:none;}

    #app{width:100%;height:660px;display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative;outline:none;}

    #phase{font-size:5.5rem;font-weight:900;text-align:center;line-height:1;transition:color 0.15s,text-shadow 0.2s;color:#333;}
    #phase.engarde{color:#fff;text-shadow:0 0 40px rgba(255,255,255,0.2);}
    #phase.prets{color:#FFC107;text-shadow:0 0 50px rgba(255,193,7,0.3);}
    #phase.allez{color:#00FF88;text-shadow:0 0 60px rgba(0,255,136,0.4);}
    #phase.stopped{color:#00AAFF;text-shadow:0 0 40px rgba(0,170,255,0.3);}

    #status{font-size:1rem;font-weight:600;color:#555;margin-top:0.8rem;letter-spacing:0.08em;transition:color 0.15s;}

    #chrono{font-family:'JetBrains Mono',monospace;font-size:5rem;font-weight:700;color:#222;margin-top:1rem;transition:color 0.15s,text-shadow 0.2s;}
    #chrono.running{color:#00FF88;text-shadow:0 0 50px rgba(0,255,136,0.3);}
    #chrono.stopped{color:#00AAFF;text-shadow:0 0 30px rgba(0,170,255,0.2);}

    #unit{font-size:0.9rem;color:#444;margin-top:0.3rem;font-family:'JetBrains Mono',monospace;}

    #heard{margin-top:1rem;font-size:0.85rem;color:#444;font-family:'JetBrains Mono',monospace;
        background:rgba(26,31,46,0.5);padding:0.4rem 1.2rem;border-radius:8px;
        border:1px solid rgba(255,255,255,0.04);min-width:220px;text-align:center;min-height:1.5rem;transition:border-color 0.15s;}
    #heard.match{border-color:#00FF88;color:#00FF88;}
    #heard.listening{border-color:rgba(255,193,7,0.3);}

    #last-result{margin-top:0.8rem;font-size:1rem;color:#555;min-height:1.5rem;}
    #last-result .rt{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:1.3rem;color:#00FF88;}

    /* Ses çubuğu */
    #mic-sec{margin-top:1.2rem;text-align:center;width:300px;}
    #mic-lbl{font-size:0.7rem;color:#444;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.3rem;}
    #mic-bg{width:100%;height:10px;background:rgba(26,31,46,0.8);border-radius:5px;overflow:hidden;border:1px solid rgba(255,255,255,0.04);}
    #mic-fill{height:100%;width:0%;border-radius:5px;background:linear-gradient(90deg,#00FF88,#00AAFF);transition:width 0.04s linear;}
    #mic-fill.hot{background:linear-gradient(90deg,#FF9100,#FF1744);}

    /* Adımlar */
    #steps{position:absolute;top:1.2rem;left:50%;transform:translateX(-50%);display:flex;gap:0.4rem;align-items:center;}
    .step{padding:0.3rem 0.8rem;border-radius:8px;font-size:0.75rem;font-weight:600;
        background:rgba(26,31,46,0.6);border:1px solid #222;color:#444;transition:all 0.2s;letter-spacing:0.05em;}
    .step.waiting{border-color:#FFC107;color:#FFC107;animation:blink 1.5s ease-in-out infinite;}
    .step.done{border-color:#00FF88;color:#00FF88;background:rgba(0,255,136,0.08);}
    .step.ready{border-color:#00FF88;color:#00FF88;animation:blink 0.8s ease-in-out infinite;}
    .step-arrow{color:#333;font-size:0.8rem;}

    @keyframes blink{0%,100%{opacity:1;}50%{opacity:0.4;}}

    #counter{position:absolute;top:1rem;right:1.5rem;font-family:'JetBrains Mono',monospace;font-size:0.85rem;color:#333;
        background:rgba(26,31,46,0.6);padding:0.4rem 0.8rem;border-radius:8px;border:1px solid rgba(255,255,255,0.04);}

    #instruction{position:absolute;bottom:1.5rem;font-size:0.78rem;color:#383838;text-align:center;line-height:1.6;}
    #instruction strong{color:#555;}

    #start-btn{padding:1rem 2.5rem;font-size:1.1rem;font-weight:700;font-family:'Inter',sans-serif;
        background:linear-gradient(135deg,#00FF88,#00CC6A);color:#000;border:none;border-radius:14px;cursor:pointer;animation:pulse 2s ease-in-out infinite;}
    #start-btn:hover{transform:scale(1.05);box-shadow:0 0 30px rgba(0,255,136,0.3);}

    #flash{position:absolute;top:0;left:0;right:0;bottom:0;pointer-events:none;opacity:0;transition:opacity 0.12s;}

    .hidden{display:none !important;}
    @keyframes pulse{0%,100%{transform:scale(1);}50%{transform:scale(1.03);}}
</style>
</head>
<body>
<div id="app" tabindex="0">
    <div id="flash"></div>

    <div id="intro">
        <div style="font-size:3rem;margin-bottom:1rem;">🎤⚔️</div>
        <p style="color:#888;margin-bottom:0.8rem;max-width:440px;text-align:center;line-height:1.7;">
            <strong style="color:#fff">"En Garde"</strong> → konuşma tanıma ile algılar<br>
            <strong style="color:#FFC107">"Prêts"</strong> → konuşma tanıma ile algılar<br>
            <strong style="color:#00FF88">"Allez!"</strong> → ses anında algılanır, kronometre <u>anında</u> başlar<br>
            Sporcu <strong style="color:#00AAFF">SPACE</strong> ile durdurur
        </p>
        <p style="color:#555;font-size:0.72rem;margin-bottom:1.5rem;">Chrome veya Edge tarayıcı önerilir</p>
        <button id="start-btn" onclick="startApp()">🎤 Başlat</button>
    </div>

    <div id="main-screen" class="hidden">
        <div id="steps">
            <div class="step waiting" id="s1">EN GARDE</div>
            <div class="step-arrow">→</div>
            <div class="step" id="s2">PRÊTS</div>
            <div class="step-arrow">→</div>
            <div class="step" id="s3">ALLEZ!</div>
        </div>
        <div id="counter">Ölçüm: <span id="cnt">0</span></div>

        <div id="phase">⚔️</div>
        <div id="status">🎤 "En Garde" deyin...</div>
        <div id="chrono">0.000</div>
        <div id="unit">saniye</div>
        <div id="heard" class="listening">dinliyor...</div>
        <div id="last-result"></div>

        <div id="mic-sec">
            <div id="mic-lbl">🎤 Ses Seviyesi</div>
            <div id="mic-bg"><div id="mic-fill"></div></div>
        </div>

        <div id="instruction">
            <strong>En Garde</strong> ve <strong>Prêts</strong> → konuşma tanıma |
            <strong>Allez!</strong> → anlık ses algılama → ⏱️ kronometre |
            <strong>SPACE</strong> → durdur
        </div>
    </div>
</div>

<script>
    // ═══════════════════════════════════════
    //  HİBRİT SİSTEM
    //  Adım 1-2: Speech Recognition (kelime tanıma)
    //  Adım 3: Web Audio API (anlık ses algılama, <5ms)
    // ═══════════════════════════════════════

    let recognition = null;
    let audioCtx = null;
    let analyser = null;
    let micStream = null;

    let currentStep = 0; // 0=en garde, 1=prets, 2=allez(ses bekle), 3=kronometre
    let isRunning = false;
    let startTime = 0;
    let chronoRAF = null;
    let measureCount = 0;
    let allResults = [];
    let cooldown = false;
    let soundWasLow = true;

    const THRESHOLD = 0.12;

    // Kelime listeleri (Türkçe okunuşlar + Fransızca yazılışlar)
    const ENGARDE = ['angart','angard','angar','angarde','angart','en garde','engarde','garde','guard','gard','en gard','on garde','on guard','en gar','gar','an gar','an gard','an garde','engard','and guard','anger','angar de','hangar','ungar'];
    const PRETS = ['pre','pire','preh','piré','pré','prêts','pret','prêt','pray','prés','prete','prête','prets','press','prep','prey','pres','bret','fred','pere','per','pire','fire','tire','bire','dire'];

    const $intro=document.getElementById('intro'), $main=document.getElementById('main-screen');
    const $phase=document.getElementById('phase'), $status=document.getElementById('status');
    const $chrono=document.getElementById('chrono'), $heard=document.getElementById('heard');
    const $lastResult=document.getElementById('last-result'), $cnt=document.getElementById('cnt');
    const $flash=document.getElementById('flash'), $app=document.getElementById('app');
    const $s1=document.getElementById('s1'), $s2=document.getElementById('s2'), $s3=document.getElementById('s3');
    const $micFill=document.getElementById('mic-fill');

    function norm(t){return t.toLowerCase().replace(/[.,!?;:'"]/g,'').replace(/\s+/g,' ').trim();}
    function has(text,list){const n=norm(text);for(const w of list)if(n.includes(w))return true;return false;}

    // ═══════════════════════════════════════
    //  BAŞLAT
    // ═══════════════════════════════════════
    async function startApp(){
        // 1. Web Audio API (anlık ses algılama için)
        const AC=window.AudioContext||window.webkitAudioContext;
        audioCtx=new AC();
        if(audioCtx.state==='suspended') await audioCtx.resume();

        try{
            micStream=await navigator.mediaDevices.getUserMedia({audio:true});
        }catch(e){alert('Mikrofon erişimi reddedildi!');return;}

        const source=audioCtx.createMediaStreamSource(micStream);
        analyser=audioCtx.createAnalyser();
        analyser.fftSize=256;
        analyser.smoothingTimeConstant=0.2;
        source.connect(analyser);

        // 2. Speech Recognition (kelime tanıma için)
        const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
        if(SR){
            recognition=new SR();
            recognition.continuous=true;
            recognition.interimResults=true;
            recognition.maxAlternatives=5;
            recognition.lang='tr-TR';
            recognition.onresult=onSpeech;
            recognition.onerror=(e)=>{if(e.error!=='no-speech'&&e.error!=='aborted')restartSR();};
            recognition.onend=()=>{if(!cooldown)try{recognition.start();}catch(e){}};
            try{recognition.start();}catch(e){}
        }

        $intro.classList.add('hidden');
        $main.classList.remove('hidden');
        $app.focus();
        resetAll();
        audioLoop();
    }

    function restartSR(){setTimeout(()=>{try{recognition.start();}catch(e){}},200);}

    // ═══════════════════════════════════════
    //  SES SEVİYESİ DÖNGÜSÜ (Web Audio - anlık)
    // ═══════════════════════════════════════
    function audioLoop(){
        const buf=new Uint8Array(analyser.frequencyBinCount);

        function tick(){
            analyser.getByteFrequencyData(buf);
            let sum=0;
            for(let i=0;i<buf.length;i++) sum+=buf[i];
            const avg=sum/buf.length/255;

            // Ses çubuğu
            const pct=Math.min(avg*500,100);
            $micFill.style.width=pct+'%';
            $micFill.classList.toggle('hot',avg>THRESHOLD);

            // Ses düştüyse bayrak sıfırla
            if(avg<THRESHOLD*0.4) soundWasLow=true;

            // ADIM 2 TAMAMLANDI → Allez bekliyor → ANLIK SES ALGILAMA
            if(currentStep===2 && avg>THRESHOLD && soundWasLow && !cooldown && !isRunning){
                soundWasLow=false;
                onAllez();
            }

            requestAnimationFrame(tick);
        }
        tick();
    }

    // ═══════════════════════════════════════
    //  KONUŞMA TANIMA (Adım 1 ve 2 için)
    // ═══════════════════════════════════════
    function onSpeech(event){
        if(cooldown||isRunning) return;

        let latest='';
        for(let i=event.resultIndex;i<event.results.length;i++){
            for(let a=0;a<event.results[i].length;a++){
                latest+=event.results[i][a].transcript+' ';
            }
        }

        const display=norm(event.results[event.results.length-1][0].transcript);
        $heard.textContent='🎤 '+display;
        $heard.className='listening';

        if(currentStep===0 && has(latest,ENGARDE)){
            onEnGarde();
        } else if(currentStep===1 && has(latest,PRETS)){
            onPrets();
        }
        // Adım 2 (Allez) artık burada DEĞİL → Web Audio ile anlık algılanıyor
    }

    // ═══════════════════════════════════════
    //  FAZLAR
    // ═══════════════════════════════════════
    function onEnGarde(){
        currentStep=1;
        $s1.className='step done';
        $s2.className='step waiting';
        $phase.textContent='⚔️ EN GARDE';
        $phase.className='engarde';
        $status.textContent='✅ Algılandı → "Prêts" deyin...';
        $status.style.color='#aaa';
        $heard.className='match';
        doFlash('#ffffff',0.08);
        briefCD(1000);
    }

    function onPrets(){
        currentStep=2;
        soundWasLow=true; // Allez için ses bayrağını sıfırla
        $s2.className='step done';
        $s3.className='step ready';
        $phase.textContent='🟡 PRÊTS';
        $phase.className='prets';
        $status.textContent='✅ Algılandı → "Allez!" deyin (anlık algılama aktif)';
        $status.style.color='#FFC107';
        $heard.textContent='⚡ Anlık ses algılama hazır...';
        $heard.className='match';
        doFlash('#FFC107',0.1);
        briefCD(1200);
    }

    function onAllez(){
        // ── ANLIK: Ses algılandığı an performance.now() ile zaman damgası ──
        currentStep=3;
        isRunning=true;
        startTime=performance.now(); // <── ANLIK ZAMAN DAMGASI

        $s3.className='step done';
        $phase.textContent='🟢 ALLEZ!';
        $phase.className='allez';
        $status.textContent='⏱️ SPACE BAS!';
        $status.style.color='#00FF88';
        $chrono.className='running';
        $heard.textContent='⏱️ Kronometre çalışıyor...';
        $heard.className='match';
        doFlash('#00FF88',0.2);

        function tick(){
            if(!isRunning)return;
            $chrono.textContent=((performance.now()-startTime)/1000).toFixed(3);
            chronoRAF=requestAnimationFrame(tick);
        }
        tick();
    }

    // ═══════════════════════════════════════
    //  SPACE → DURDUR
    // ═══════════════════════════════════════
    function stopChrono(){
        if(!isRunning)return;
        const elapsed=performance.now()-startTime;
        isRunning=false;
        if(chronoRAF)cancelAnimationFrame(chronoRAF);

        const sec=(elapsed/1000).toFixed(3);
        const ms=elapsed.toFixed(1);
        $chrono.textContent=sec;
        $chrono.className='stopped';
        $phase.textContent='✅ '+ms+' ms';
        $phase.className='stopped';
        $status.textContent='Kaydedildi!';
        $status.style.color='#00AAFF';
        $heard.textContent='✅ '+ms+' ms';
        $heard.className='match';
        doFlash('#00AAFF',0.12);

        measureCount++;
        $cnt.textContent=measureCount;
        $lastResult.innerHTML='Son: <span class="rt">'+ms+' ms</span>';

        allResults.push({number:measureCount,reaction_time_ms:parseFloat(ms),timestamp:Date.now()});

        window.parent.postMessage({
            isStreamlitMessage:true,type:'streamlit:setComponentValue',
            value:{status:'RESULT',count:measureCount,reaction_time_ms:parseFloat(ms),all_results:allResults}
        },'*');

        cooldown=true;
        setTimeout(()=>{cooldown=false;resetAll();restartSR();},2500);
    }

    // ═══════════════════════════════════════
    //  YARDIMCI
    // ═══════════════════════════════════════
    function resetAll(){
        currentStep=0;isRunning=false;soundWasLow=true;
        $s1.className='step waiting';$s2.className='step';$s3.className='step';
        $phase.textContent='⚔️';$phase.className='';
        $chrono.textContent='0.000';$chrono.className='';
        $status.textContent='🎤 "En Garde" deyin...';$status.style.color='#555';
        $heard.textContent='dinliyor...';$heard.className='listening';
    }

    function briefCD(ms){cooldown=true;setTimeout(()=>{cooldown=false;},ms);}

    function doFlash(hex,a){
        const r=parseInt(hex.slice(1,3),16),g=parseInt(hex.slice(3,5),16),b=parseInt(hex.slice(5,7),16);
        $flash.style.background='rgba('+r+','+g+','+b+','+a+')';
        $flash.style.opacity='1';
        setTimeout(()=>{$flash.style.opacity='0';},250);
    }

    document.addEventListener('keydown',(e)=>{
        if(e.code==='Space'||e.code==='Enter'){e.preventDefault();if(!e.repeat)stopChrono();}
    },{passive:false,capture:true});
    $app.addEventListener('click',()=>{if(isRunning)stopChrono();});
    $app.focus();

    window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:componentReady',apiVersion:1},'*');
    window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:680},'*');
</script>
</body>
</html>
"""

import streamlit.components.v1 as components
components.html(component_html, height=680, scrolling=False)

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
    st.info("👆 Başlat → Antrenör: En Garde, Prêts, Allez! → Sporcu: SPACE")
