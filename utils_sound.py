"""
utils_sound.py — Sons de notification pour DarPharm Solution
Utilise l'API Web Audio du navigateur (aucun fichier audio requis).
"""
import streamlit.components.v1 as components

def play_sound(sound_type: str = "notification"):
    """
    Joue un son de notification dans le navigateur via Web Audio API.
    
    sound_type:
        "notification" — Ding court (nouvelle alerte)
        "mission"      — Double ping (nouvelle mission / coordination)
        "ai"           — Mélodie douce (réponse IA)
        "success"      — Accord montant (succès / validation)
        "warning"      — Son grave (alerte critique)
    """
    
    sounds = {
        "notification": """
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.type = 'sine';
            osc.frequency.setValueAtTime(880, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(660, ctx.currentTime + 0.15);
            gain.gain.setValueAtTime(0.4, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.4);
        """,
        
        "mission": """
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            [0, 0.18].forEach(delay => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain); gain.connect(ctx.destination);
                osc.type = 'sine';
                osc.frequency.setValueAtTime(1046, ctx.currentTime + delay);
                gain.gain.setValueAtTime(0.35, ctx.currentTime + delay);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + delay + 0.3);
                osc.start(ctx.currentTime + delay);
                osc.stop(ctx.currentTime + delay + 0.3);
            });
        """,
        
        "ai": """
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const notes = [523, 659, 784];
            notes.forEach((freq, i) => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain); gain.connect(ctx.destination);
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(freq, ctx.currentTime + i * 0.12);
                gain.gain.setValueAtTime(0.25, ctx.currentTime + i * 0.12);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.12 + 0.3);
                osc.start(ctx.currentTime + i * 0.12);
                osc.stop(ctx.currentTime + i * 0.12 + 0.3);
            });
        """,
        
        "success": """
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const notes = [523, 659, 784, 1046];
            notes.forEach((freq, i) => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain); gain.connect(ctx.destination);
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq, ctx.currentTime + i * 0.1);
                gain.gain.setValueAtTime(0.3, ctx.currentTime + i * 0.1);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.1 + 0.25);
                osc.start(ctx.currentTime + i * 0.1);
                osc.stop(ctx.currentTime + i * 0.1 + 0.25);
            });
        """,
        
        "warning": """
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            [0, 0.25, 0.5].forEach(delay => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain); gain.connect(ctx.destination);
                osc.type = 'sawtooth';
                osc.frequency.setValueAtTime(220, ctx.currentTime + delay);
                gain.gain.setValueAtTime(0.3, ctx.currentTime + delay);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + delay + 0.2);
                osc.start(ctx.currentTime + delay);
                osc.stop(ctx.currentTime + delay + 0.2);
            });
        """
    }
    
    js_code = sounds.get(sound_type, sounds["notification"])
    
    components.html(f"""
        <script>
            (function() {{
                try {{
                    {js_code}
                }} catch(e) {{
                    console.warn('Son non supporté :', e);
                }}
            }})();
        </script>
    """, height=0, scrolling=False)
