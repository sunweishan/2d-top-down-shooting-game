"""
audio.py - Sound generation, audio management, and spatial stereo audio engine.
Synthesizes 16-bit PCM WAV audio effects programmatically to guarantee zero missing asset issues.
"""

import io
import math
import random
import struct
import wave
import pygame

SAMPLE_RATE = 22050  # 22.05 kHz standard game audio sample rate
MAX_AUDIO_DIST = 850.0  # Max distance in pixels for audible sound


def _create_wav(samples):
    """Encodes a list of float audio samples (-1.0 to 1.0) into in-memory WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)  # Mono raw sample, panned dynamically in mixer
        wav.setsampwidth(2)   # 16-bit
        wav.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for s in samples:
            clamped = max(-1.0, min(1.0, s))
            val = int(clamped * 32767)
            frames.extend(struct.pack('<h', val))
        wav.writeframes(frames)
    buf.seek(0)
    return buf


def _generate_gunshot():
    """Sharp transient attack, decaying noisy explosion and bass thump."""
    duration = 0.22
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-18.0 * t)
        noise = (random.random() * 2.0 - 1.0) * 0.65
        thump = math.sin(2.0 * math.pi * 95.0 * math.exp(-12.0 * t) * t) * 0.45
        sample = (noise + thump) * env
        samples.append(sample)
    return _create_wav(samples)


def _generate_knife_slash():
    """High-speed blade whoosh / frequency sweep."""
    duration = 0.18
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.sin(math.pi * (t / duration)) ** 1.5
        freq = 900.0 - 450.0 * (t / duration)
        sine = math.sin(2.0 * math.pi * freq * t)
        noise = (random.random() * 2.0 - 1.0) * 0.35
        samples.append((sine * 0.6 + noise * 0.4) * env * 0.8)
    return _create_wav(samples)


def _generate_knife_hit():
    """Flesh stab / heavy blade strike impact."""
    duration = 0.25
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-16.0 * t)
        sub = math.sin(2.0 * math.pi * 70.0 * t) * 0.6
        crunch = (random.random() * 2.0 - 1.0) * 0.5 * math.exp(-35.0 * t)
        samples.append((sub + crunch) * env)
    return _create_wav(samples)


def _generate_bullet_hit_body():
    """Dull body impact thud."""
    duration = 0.14
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-22.0 * t)
        thump = math.sin(2.0 * math.pi * 85.0 * t) * 0.7
        click = (random.random() * 2.0 - 1.0) * 0.3 * math.exp(-40.0 * t)
        samples.append((thump + click) * env)
    return _create_wav(samples)


def _generate_bullet_hit_wall():
    """High-pitched metallic ricochet ping and spark crackle."""
    duration = 0.22
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-15.0 * t)
        # Chirp frequency
        freq = 1600.0 + 400.0 * math.sin(2.0 * math.pi * 35.0 * t)
        ping = math.sin(2.0 * math.pi * freq * t) * 0.5
        grit = (random.random() * 2.0 - 1.0) * 0.4 * math.exp(-30.0 * t)
        samples.append((ping + grit) * env * 0.7)
    return _create_wav(samples)


def _generate_footstep():
    """Subtle tactical boot step tap on concrete."""
    duration = 0.08
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.sin(math.pi * (t / duration)) * math.exp(-25.0 * t)
        thud = math.sin(2.0 * math.pi * 90.0 * t) * 0.5
        scuff = (random.random() * 2.0 - 1.0) * 0.3
        samples.append((thud + scuff) * env * 0.45)
    return _create_wav(samples)


def _generate_alert():
    """Tactical radio beep / target acquired blip."""
    duration = 0.16
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        freq = 880.0 if t < 0.08 else 1250.0
        env = math.sin(math.pi * (t / duration)) ** 0.5
        beep = math.sin(2.0 * math.pi * freq * t) * 0.5
        samples.append(beep * env * 0.6)
    return _create_wav(samples)


def _generate_victory():
    """Triumphant synthesized ascending fanfare triad."""
    duration = 1.0
    num_samples = int(SAMPLE_RATE * duration)
    notes = [523.25, 659.25, 783.99, 1046.50]  # C5, E5, G5, C6
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        note_idx = min(len(notes) - 1, int(t / 0.22))
        freq = notes[note_idx]
        t_note = t - note_idx * 0.22
        env = math.exp(-3.0 * t_note) if note_idx < 3 else math.exp(-1.5 * t_note)
        tone = (
            math.sin(2.0 * math.pi * freq * t) * 0.5
            + math.sin(2.0 * math.pi * freq * 2.0 * t) * 0.25
        )
        samples.append(tone * env * 0.5)
    return _create_wav(samples)


def _generate_defeat():
    """Low somber dramatic descending sting."""
    duration = 1.2
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        freq = max(55.0, 220.0 - 130.0 * (t / duration))
        env = math.exp(-1.8 * t)
        rumble = (
            math.sin(2.0 * math.pi * freq * t) * 0.6
            + math.sin(2.0 * math.pi * (freq * 1.5) * t) * 0.3
        )
        samples.append(rumble * env * 0.6)
    return _create_wav(samples)


def _generate_medkit_pickup():
    """Refreshing ascending harmonic chime on supply pickup."""
    duration = 0.38
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    notes = [587.33, 880.00, 1174.66]  # D5, A5, D6
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        n_idx = min(len(notes) - 1, int(t / 0.11))
        freq = notes[n_idx]
        t_note = t - n_idx * 0.11
        env = math.exp(-6.0 * t_note)
        tone = math.sin(2.0 * math.pi * freq * t) * 0.5 + math.sin(2.0 * math.pi * freq * 2.0 * t) * 0.2
        samples.append(tone * env * 0.6)
    return _create_wav(samples)


def _generate_menu_select():
    """Crisp high-tech UI selection click."""
    duration = 0.05
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-35.0 * t)
        click = math.sin(2.0 * math.pi * 1400.0 * t) * 0.5
        samples.append(click * env * 0.5)
    return _create_wav(samples)


def _generate_sniper_shot():
    """Heavy high-caliber rifle crack with echoing acoustic tail."""
    duration = 0.38
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-11.0 * t)
        crack = (random.random() * 2.0 - 1.0) * math.exp(-40.0 * t) * 0.8
        boom = math.sin(2.0 * math.pi * (140.0 * math.exp(-8.0 * t)) * t) * 0.6
        tail = math.sin(2.0 * math.pi * 55.0 * t) * 0.25 * math.exp(-5.0 * t)
        samples.append((crack + boom + tail) * env)
    return _create_wav(samples)


def _generate_rocket_launch():
    """Rocket propulsion thrust whoosh and ignition roar."""
    duration = 0.32
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.sin(math.pi * min(1.0, t / 0.08)) * math.exp(-4.5 * t)
        noise = (random.random() * 2.0 - 1.0) * 0.55
        tone = math.sin(2.0 * math.pi * (180.0 + 80.0 * math.sin(15.0 * t)) * t) * 0.45
        samples.append((noise + tone) * env * 0.8)
    return _create_wav(samples)


def _generate_explosion():
    """Deep low-frequency detonation rumble and blast shockwave."""
    duration = 0.55
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-7.0 * t)
        blast = (random.random() * 2.0 - 1.0) * math.exp(-22.0 * t) * 0.85
        rumble = math.sin(2.0 * math.pi * (65.0 * math.exp(-3.5 * t)) * t) * 0.65
        sub = math.sin(2.0 * math.pi * 38.0 * t) * 0.35 * math.exp(-4.0 * t)
        samples.append((blast + rumble + sub) * env)
    return _create_wav(samples)


class AudioManager:
    """Manages audio loading, playback, and positional 2D stereo panning."""

    def __init__(self):
        self.sounds = {}
        self.enabled = True
        self._init_mixer()

    def _init_mixer(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(24)  # Plenty of channels for intense firefights
            self._load_sounds()
        except Exception as e:
            print(f"[AudioManager] Audio device unavailable ({e}); running in silent mode.")
            self.enabled = False

    def _load_sounds(self):
        """Synthesize all game sound effects and load into Pygame Sound objects."""
        generators = {
            'gunshot': _generate_gunshot,
            'sniper_shot': _generate_sniper_shot,
            'rocket_launch': _generate_rocket_launch,
            'explosion': _generate_explosion,
            'knife_slash': _generate_knife_slash,
            'knife_hit': _generate_knife_hit,
            'hit_body': _generate_bullet_hit_body,
            'hit_wall': _generate_bullet_hit_wall,
            'footstep': _generate_footstep,
            'alert': _generate_alert,
            'victory': _generate_victory,
            'defeat': _generate_defeat,
            'medkit_pickup': _generate_medkit_pickup,
            'menu_select': _generate_menu_select,
        }
        for name, gen in generators.items():
            try:
                wav_io = gen()
                self.sounds[name] = pygame.mixer.Sound(wav_io)
            except Exception as e:
                print(f"[AudioManager] Failed to generate {name}: {e}")

    def play(self, sound_name, volume=1.0):
        """Plays a 2D non-spatial sound (UI, player fire, announcements)."""
        if not self.enabled or sound_name not in self.sounds:
            return
        sound = self.sounds[sound_name]
        ch = pygame.mixer.find_channel()
        if ch:
            ch.set_volume(volume, volume)
            ch.play(sound)

    def play_spatial(self, sound_name, sound_pos, listener_pos, screen_width=1280, base_volume=1.0):
        """
        Plays sound with positional 2D stereo panning and distance falloff.
        
        sound_pos: (x, y) world position of sound source
        listener_pos: (x, y) world position of player
        """
        if not self.enabled or sound_name not in self.sounds:
            return

        dx = sound_pos[0] - listener_pos[0]
        dy = sound_pos[1] - listener_pos[1]
        dist = math.hypot(dx, dy)

        if dist > MAX_AUDIO_DIST:
            return  # Out of hearing range

        # Distance attenuation with natural quadratic curve
        dist_factor = max(0.0, min(1.0, 1.0 - (dist / MAX_AUDIO_DIST))) ** 1.3

        # Pan ratio: -1.0 (hard left) to +1.0 (hard right)
        pan_span = screen_width * 0.55
        pan = max(-1.0, min(1.0, dx / pan_span))

        # Stereo channel distribution
        # When sound is left (pan < 0), right channel drops; when sound is right (pan > 0), left channel drops.
        left_factor = max(0.08, min(1.0, 1.0 - (pan + 1.0) * 0.42))
        right_factor = max(0.08, min(1.0, 1.0 - (1.0 - pan) * 0.42))

        left_vol = base_volume * dist_factor * left_factor
        right_vol = base_volume * dist_factor * right_factor

        ch = pygame.mixer.find_channel()
        if ch:
            ch.set_volume(left_vol, right_vol)
            ch.play(self.sounds[sound_name])
