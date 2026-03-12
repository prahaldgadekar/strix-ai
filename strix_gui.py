"""
strix_gui.py — STRIX v3.0
===========================
GUI upgrades:
  1. Model badge on every STRIX bubble  (shows phi3 / llama3.1 / qwen2.5-coder)
  2. Typing indicator  (animated dots while model is thinking)
  3. Smooth streaming  (text flows in cleanly, no flicker)
  4. STOP button only shows during streaming
  5. Weather fixed     (uses wttr.in fallback, no API key needed)
  6. Window remembers size and position
  7. Right panel shows active model per role
  8. Better code bubbles with syntax highlighting colors
"""

import sys, os, math, threading, re, time, json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QFrame, QScrollArea,
    QSizePolicy, QComboBox, QFileDialog,
)
from PySide6.QtCore  import Qt, QTimer, QThread, Signal, QRectF, Slot, QSettings, QPoint, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui   import (
    QColor, QPainter, QPen, QBrush, QPalette,
    QLinearGradient, QRadialGradient, QConicalGradient, QFont, QPixmap,
    QShortcut, QKeySequence, QScreen,
)
import base64

# ── Colours ───────────────────────────────────────────────────
BG    = "#050912"
BG2   = "#080f1e"
CYAN  = "#00e5ff"
CYAN2 = "#0088cc"
CYAN3 = "#00ffcc"
GOLD  = "#ffd700"
ROG   = "#ff0033"
DIM   = "#1a3050"
TEXT  = "#c8e8ff"
TDIM  = "#3a6080"
GREEN = "#00ff88"

# Model badge colours
MODEL_COLORS = {
    "phi3":          "#ff6600",   # orange  — fast chat
    "phi3:latest":   "#ff6600",
    "llama3.1":      "#aa44ff",   # purple  — reasoning
    "llama3.1:latest":"#aa44ff",
    "qwen2.5-coder": "#00cc44",   # green   — coding
    "qwen2.5-coder:latest": "#00cc44",
    "default":       ROG,
}

HUD_B64 = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAUDBAQEAwUEBAQFBQUGBwwIBwcHBw8LCwkMEQ8SEhEPERETFhwXExQaFRERGCEYGh0dHx8fExciJCIeJBweHx7/wAARCABkAGQDASIAAhEBAxEB/8QAGwABAAMBAQEBAAAAAAAAAAAAAAQFBgMCB//EADMQAAIBAwIDBgQFBQAAAAAAAAECAwAEEQUSITFBUWEGEyJxgZEyQqGxwRQjUmJy0fD/xAAUAQEAAAAAAAAAAAAAAAAAAAAA/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8A/R6UpQClKUApSlAKUpQClKUApSlAKUpQClKUApSlAKUpQClKUApSlAKUpQClKUApSlAKUpQClKUApSlAKUpQClKUApSlAKUpQClKUApSlAKUpQClKUApSlAKUpQClKUApSlAKUpQClKUApSlAKUpQClKUApSlAKUpQClKUApSlAKUpQClKUApSlAKUpQClKUApSlAKUpQClKUApSlAf/2Q=="


def clean_text(text: str) -> str:
    """Clean text for display — removes markdown symbols."""
    text = re.sub(r'```[\s\S]*?```', '[code block]', text)
    text = re.sub(r'`[^`]*`', '', text)
    for ch in ['*','#','_','`','\\','|','^','~','[',']','{','}','<','>','@']:
        text = text.replace(ch,'')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def tts_clean(text: str) -> str:
    """
    Clean text for TTS — converts symbols to spoken words,
    removes markdown, keeps only speakable content.
    """
    # Remove code blocks entirely (don't read raw code)
    text = re.sub(r'```[\s\S]*?```', 'code block here.', text)
    text = re.sub(r'`[^`]*`', '', text)
    # Speak common symbols as words
    replacements = [
        ('#',  ''),        ('*',  ''),        ('_',  ''),
        ('\\', ''),        ('|',  ''),        ('^',  ''),
        ('~',  ''),        ('@',  ''),
        (';',  '.'),       ('/',  ' slash '),
        (':',  '.'),       ('->','arrow'),
        ('=>', 'returns'), ('!=','not equal'),
        ('==', 'equals'),  ('>=','greater or equal'),
        ('<=', 'less or equal'),
        ('[',  ''),        (']',  ''),
        ('{',  ''),        ('}',  ''),
        ('<',  ''),        ('>',  ''),
        ('(',  ''),        (')',  ''),
    ]
    for sym, word in replacements:
        text = text.replace(sym, word)
    # Clean up extra spaces
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\n+', '. ', text)
    text = text.strip()
    # NO cap — let strix_tts.py handle full text
    return text


def detect_code_blocks(text: str) -> list:
    pattern = re.compile(r'```(\w*)\n?([\s\S]*?)```', re.MULTILINE)
    segments = []
    last = 0
    for m in pattern.finditer(text):
        if m.start() > last:
            segments.append({"type":"text","content":text[last:m.start()],"lang":""})
        segments.append({"type":"code","content":m.group(2).rstrip(),"lang":m.group(1) or "code"})
        last = m.end()
    if last < len(text):
        segments.append({"type":"text","content":text[last:],"lang":""})
    return segments or [{"type":"text","content":text,"lang":""}]


def model_badge_color(model: str) -> str:
    for k, v in MODEL_COLORS.items():
        if k in model.lower():
            return v
    return MODEL_COLORS["default"]


def model_short_name(model: str) -> str:
    if "qwen" in model.lower():   return "QWEN-CODER"
    if "llama" in model.lower():  return "LLAMA3.1"
    if "phi" in model.lower():    return "PHI3"
    if "mistral" in model.lower():return "MISTRAL"
    return model.upper()[:10]



import random

# ── Corner bracket animator ───────────────────────────────────
class CornerBrackets(QWidget):
    """Pulsing ROG corner brackets drawn on top of the main window."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._pulse = 0.0
        self._pdir  = 1
        self._spin  = 0.0
        t = QTimer(self); t.timeout.connect(self._tick); t.start(30)

    def _tick(self):
        self._pulse += 0.03 * self._pdir
        if self._pulse >= 1.0 or self._pulse <= 0.0:
            self._pdir *= -1
        self._spin = (self._spin + 0.4) % 360
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        alpha = int(80 + self._pulse * 120)
        length = 28
        thick  = 2

        # ROG red brackets at corners
        p.setPen(QPen(QColor(255, 0, 51, alpha), thick))
        corners = [
            (0, 0,  1,  1),   # top-left
            (w, 0, -1,  1),   # top-right
            (0, h,  1, -1),   # bottom-left
            (w, h, -1, -1),   # bottom-right
        ]
        for cx, cy, dx, dy in corners:
            p.drawLine(cx, cy, cx + dx*length, cy)
            p.drawLine(cx, cy, cx, cy + dy*length)

        # Cyan inner brackets — slightly inset, offset pulse
        alpha2 = int(40 + self._pulse * 80)
        p.setPen(QPen(QColor(0, 229, 255, alpha2), 1))
        pad = 8
        for cx, cy, dx, dy in corners:
            bx = cx + dx*pad
            by = cy + dy*pad
            p.drawLine(bx, by, bx + dx*(length-4), by)
            p.drawLine(bx, by, bx, by + dy*(length-4))

        p.end()


# ── Particle system ───────────────────────────────────────────
class ParticleField(QWidget):
    """Ambient floating particles in the background."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._particles = []
        self._init_particles()
        t = QTimer(self); t.timeout.connect(self._tick); t.start(40)

    def _init_particles(self):
        self._particles = []
        for _ in range(35):
            self._particles.append(self._make_particle())

    def _make_particle(self, x=None):
        w = max(self.width(), 1200)
        h = max(self.height(), 800)
        return {
            'x': x if x is not None else random.uniform(0, w),
            'y': random.uniform(0, h),
            'vy': random.uniform(-0.3, -0.9),
            'vx': random.uniform(-0.2, 0.2),
            'size': random.uniform(1, 3),
            'alpha': random.randint(20, 80),
            'color': random.choice([
                QColor(0, 229, 255),    # cyan
                QColor(255, 0, 51),     # red
                QColor(255, 215, 0),    # gold
                QColor(0, 255, 136),    # green
            ]),
            'life': random.uniform(0.4, 1.0),
        }

    def _tick(self):
        w, h = max(self.width(), 1), max(self.height(), 1)
        for i, pt in enumerate(self._particles):
            pt['x'] += pt['vx']
            pt['y'] += pt['vy']
            pt['life'] -= 0.003
            if pt['y'] < -10 or pt['life'] <= 0:
                # Replace dead particle with a fresh one at bottom
                self._particles[i] = self._make_particle(x=random.uniform(0, w))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for pt in self._particles:
            col = QColor(pt['color'])
            col.setAlpha(int(pt['alpha'] * pt['life']))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(col))
            s = pt['size']
            p.drawEllipse(QRectF(pt['x'] - s/2, pt['y'] - s/2, s, s))
        p.end()


# ── ROG Loading / Splash Screen ───────────────────────────────
BOOT_LINES = [
    "INITIALIZING NEURAL CORE...",
    "LOADING AI MODELS...",
    "CALIBRATING VOICE ENGINE...",
    "ESTABLISHING SYSTEM LINK...",
    "STRIX ONLINE.",
]


# ── Glitch Button — HUD style with scan-line glitch on click ─
class GlitchButton(QPushButton):
    """
    CRT-style HUD button with:
    - Scanline texture drawn via paintEvent
    - Angled corner cuts (like image 1)
    - Continuous glitch on hover
    - RGB flash on click
    """
    def __init__(self, text, color=None, parent=None):
        super().__init__(text, parent)
        self._base_color  = color or "#00e5ff"
        self._glitch_on   = False
        self._glitch_step = 0
        self._hover       = False
        self._scan_offset = 0
        self._glitch_shift = 0   # pixel shift for glitch effect
        self._current_col = self._base_color
        self._glitch_colors = [
            "#ff0033","#00e5ff","#ffd700","#00ff88",
            "#ff00ff","#ffffff","#ff0033","#00e5ff",
        ]
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._glitch_tick)
        self._hover_timer = QTimer(self)
        self._hover_timer.timeout.connect(self._hover_tick)
        self.setFixedHeight(34)
        self.setMinimumWidth(80)
        # Transparent base so we can paint everything ourselves
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: transparent;
                font-family: Consolas;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 2px;
                padding: 0px 18px;
            }
        """)
        self.setCursor(Qt.PointingHandCursor)

    def _hex_to_qcolor(self, h):
        h = h.lstrip("#")
        r,g,b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        return QColor(r,g,b)

    def _hover_tick(self):
        """Animate scanlines + subtle glitch while hovering."""
        self._scan_offset = (self._scan_offset + 2) % 8
        if random.random() < 0.3:
            self._glitch_shift = random.randint(-3, 3)
        else:
            self._glitch_shift = 0
        self.update()

    def _glitch_tick(self):
        if self._glitch_step >= len(self._glitch_colors):
            self._timer.stop()
            self._glitch_on = False
            self._glitch_step = 0
            self._current_col = self._base_color
            self._glitch_shift = 0
            self.update()
            return
        self._current_col = self._glitch_colors[self._glitch_step]
        self._glitch_shift = random.randint(-5, 5)
        self._glitch_step += 1
        self.update()

    def trigger_glitch(self):
        self._glitch_on   = True
        self._glitch_step = 0
        self._timer.start(45)

    def mousePressEvent(self, e):
        self.trigger_glitch()
        super().mousePressEvent(e)

    def enterEvent(self, e):
        self._hover = True
        self._hover_timer.start(40)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self._hover_timer.stop()
        self._glitch_shift = 0
        self._scan_offset = 0
        self.update()
        super().leaveEvent(e)

    def set_active(self, active: bool, active_color="#00ff88"):
        self._base_color  = active_color if active else "#00e5ff"
        self._current_col = self._base_color
        self.trigger_glitch()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        col = self._hex_to_qcolor(self._current_col if self._glitch_on else self._base_color)

        # ── Background fill ───────────────────────────────
        bg_alpha = 220 if self._hover else 200
        p.setPen(Qt.NoPen)
        if self._hover and not self._glitch_on:
            p.setBrush(QBrush(QColor(col.red()//6, col.green()//6, col.blue()//6, bg_alpha)))
        else:
            p.setBrush(QBrush(QColor(0, 15, 30, bg_alpha)))

        # Angled corners polygon (CRT style like image 1)
        cut = 6
        from PySide6.QtGui import QPolygon
        from PySide6.QtCore import QPoint
        poly = QPolygon([
            QPoint(cut, 0),
            QPoint(w - cut, 0),
            QPoint(w, cut),
            QPoint(w, h - cut),
            QPoint(w - cut, h),
            QPoint(cut, h),
            QPoint(0, h - cut),
            QPoint(0, cut),
        ])
        p.drawPolygon(poly)

        # ── Scanlines inside button ───────────────────────
        scan_alpha = 35 if self._hover else 20
        p.setPen(QPen(QColor(0, 0, 0, scan_alpha), 1))
        offset = self._scan_offset if self._hover else 0
        for y in range(offset % 3, h, 3):
            p.drawLine(1, y, w-1, y)

        # ── CRT glow band (horizontal sweep on hover) ─────
        if self._hover:
            glow = QLinearGradient(0, 0, w, 0)
            glow.setColorAt(0,   QColor(col.red(), col.green(), col.blue(), 0))
            glow.setColorAt(0.4, QColor(col.red(), col.green(), col.blue(), 25))
            glow.setColorAt(0.6, QColor(col.red(), col.green(), col.blue(), 25))
            glow.setColorAt(1,   QColor(col.red(), col.green(), col.blue(), 0))
            p.setBrush(QBrush(glow))
            p.setPen(Qt.NoPen)
            p.drawPolygon(poly)

        # ── Border ────────────────────────────────────────
        border_w = 2 if self._hover or self._glitch_on else 1
        border_alpha = 255 if self._hover or self._glitch_on else 180
        p.setPen(QPen(QColor(col.red(), col.green(), col.blue(), border_alpha), border_w))
        p.setBrush(Qt.NoBrush)
        p.drawPolygon(poly)

        # ── Corner accent brackets (top-left, bottom-right) ─
        accent_col = QColor(col.red(), col.green(), col.blue(), 255)
        p.setPen(QPen(accent_col, 2))
        # top-left
        p.drawLine(0, cut, 0, cut + 8)
        p.drawLine(cut, 0, cut + 8, 0)
        # bottom-right
        p.drawLine(w, h - cut, w, h - cut - 8)
        p.drawLine(w - cut, h, w - cut - 8, h)

        # ── Glitch RGB offset strips ──────────────────────
        if self._glitch_shift != 0:
            shift = self._glitch_shift
            strip_h = random.randint(2, 6)
            strip_y = random.randint(2, h - strip_h - 2)
            # red channel offset
            p.setOpacity(0.4)
            p.setPen(QPen(QColor(255, 0, 0, 120), 1))
            p.drawLine(shift, strip_y, w + shift, strip_y)
            # cyan channel offset
            p.setPen(QPen(QColor(0, 255, 255, 120), 1))
            p.drawLine(-shift, strip_y + 2, w - shift, strip_y + 2)
            p.setOpacity(1.0)

        # ── Text ──────────────────────────────────────────
        text_col = QColor(255, 255, 255) if self._hover or self._glitch_on else col
        p.setPen(QPen(text_col))
        font = QFont("Consolas", 10, QFont.Bold)
        p.setFont(font)
        # Glitch text shift
        tx = self._glitch_shift // 2 if self._glitch_on else 0
        p.drawText(QRectF(tx, 0, w, h), Qt.AlignCenter, self.text())

        p.end()


class StrixSplash(QWidget):
    """
    Full-screen ROG themed loading screen.
    Shown before StrixWindow opens.
    Emits finished() when boot sequence is done.
    """
    finished = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(860, 520)

        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2,
        )

        self._angle    = 0.0
        self._pulse    = 0.0
        self._pdir     = 1
        self._step     = 0
        self._lines    = []
        self._bar      = 0.0
        self._done     = False
        self._alpha    = 255

        # Glitch state
        self._glitch_active  = False
        self._glitch_frame   = 0
        self._glitch_strips  = []   # list of (y, h, shift, color)
        self._s_offset_x     = 0
        self._s_offset_y     = 0
        self._bar_rgb_phase  = 0.0  # for RGB bar animation

        # Timers
        self._anim_t = QTimer(self)
        self._anim_t.timeout.connect(self._anim_tick)
        self._anim_t.start(25)

        self._line_t = QTimer(self)
        self._line_t.timeout.connect(self._next_line)
        self._line_t.start(600)

        self._fade_t = QTimer(self)
        self._fade_t.timeout.connect(self._fade_tick)

        self._glitch_t = QTimer(self)
        self._glitch_t.timeout.connect(self._glitch_tick)

    # ── animation tick ────────────────────────────────────
    def _anim_tick(self):
        self._angle = (self._angle + 1.5) % 360
        self._pulse += 0.05 * self._pdir
        if self._pulse >= 1.0 or self._pulse <= 0.0:
            self._pdir *= -1
        self._bar_rgb_phase = (self._bar_rgb_phase + 0.015) % 1.0
        self.update()

    def _glitch_tick(self):
        """Generate random glitch strips for the pre-open glitch burst."""
        self._glitch_frame += 1
        self._glitch_strips = []
        w, h = self.width(), self.height()
        # Generate 4-10 random glitch strips
        for _ in range(random.randint(4, 10)):
            gy  = random.randint(0, h)
            gh  = random.randint(1, 12)
            gsh = random.randint(-40, 40)
            gc  = random.choice([
                QColor(255,0,51,180), QColor(0,229,255,180),
                QColor(255,215,0,150), QColor(0,255,136,150),
                QColor(255,0,255,140),
            ])
            self._glitch_strips.append((gy, gh, gsh, gc))
        # S icon also jumps around
        self._s_offset_x = random.randint(-6, 6)
        self._s_offset_y = random.randint(-4, 4)
        if self._glitch_frame > 18:   # ~0.9 seconds of glitch
            self._glitch_t.stop()
            self._glitch_active = False
            self._glitch_strips = []
            self._s_offset_x = 0
            self._s_offset_y = 0
            QTimer.singleShot(100, self._start_fade)
        self.update()

    # ── reveal lines one by one ───────────────────────────
    def _next_line(self):
        if self._step < len(BOOT_LINES):
            self._lines.append(BOOT_LINES[self._step])
            self._bar = (self._step + 1) / len(BOOT_LINES)
            self._step += 1
            self.update()
        else:
            self._line_t.stop()
            self._done = True
            # Glitch burst BEFORE fading out
            QTimer.singleShot(400, self._start_glitch)

    def _start_glitch(self):
        self._glitch_active = True
        self._glitch_frame  = 0
        self._glitch_t.start(50)   # ~20fps glitch for ~0.9s

    def _start_fade(self):
        self._fade_t.start(20)

    def _fade_tick(self):
        self._alpha = max(0, self._alpha - 12)
        self.setWindowOpacity(self._alpha / 255.0)
        self.update()
        if self._alpha <= 0:
            self._fade_t.stop()
            self.finished.emit()
            self.close()

    # ── draw ──────────────────────────────────────────────
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()
        cx = w // 2

        # ════════════════════════════════════════════════
        # BACKGROUND — deep dark with subtle vignette
        # ════════════════════════════════════════════════
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0,   QColor(8,  10, 18, 255))
        bg.setColorAt(0.5, QColor(5,  7,  14, 255))
        bg.setColorAt(1,   QColor(3,  4,  10, 255))
        p.fillRect(0, 0, w, h, bg)

        # Vignette
        vig = QRadialGradient(cx, h//2, max(w, h) * 0.65)
        vig.setColorAt(0,   QColor(0, 0, 0, 0))
        vig.setColorAt(0.7, QColor(0, 0, 0, 0))
        vig.setColorAt(1,   QColor(0, 0, 0, 140))
        p.fillRect(0, 0, w, h, vig)

        # Subtle horizontal scanlines across whole panel
        p.setOpacity(0.025)
        p.setPen(QPen(QColor(0, 0, 0, 255), 1))
        for sy in range(0, h, 2):
            p.drawLine(0, sy, w, sy)
        p.setOpacity(1.0)

        # ════════════════════════════════════════════════
        # OUTER BORDER — angled ROG frame
        # ════════════════════════════════════════════════
        bc  = QColor(255, 0, 51, 200) if not self._glitch_active else QColor(0, 229, 255, 255)
        bc2 = QColor(255, 0, 51,  60)

        # Outer glow border
        pen_glow = QPen(bc2, 6)
        p.setPen(pen_glow)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(2, 2, w-4, h-4, 3, 3)

        # Main border
        p.setPen(QPen(bc, 1))
        p.drawRoundedRect(4, 4, w-8, h-8, 2, 2)

        # Corner brackets — long elegant arms
        arm = 40
        thick = QPen(bc, 2)
        thin  = QPen(QColor(bc.red(), bc.green(), bc.blue(), 120), 1)
        for bx, by, dx, dy in [(0,0,1,1),(w,0,-1,1),(0,h,1,-1),(w,h,-1,-1)]:
            p.setPen(thick)
            p.drawLine(bx + dx*6,  by,         bx + dx*(6+arm), by)
            p.drawLine(bx,         by + dy*6,  bx,              by + dy*(6+arm))
            # Inner parallel lines (double bracket)
            p.setPen(thin)
            p.drawLine(bx + dx*6,  by + dy*4,  bx + dx*(6+arm//2), by + dy*4)
            p.drawLine(bx + dx*4,  by + dy*6,  bx + dx*4,          by + dy*(6+arm//2))

        # Top edge label — right side
        p.setFont(QFont("Consolas", 7))
        p.setPen(QPen(QColor(255, 0, 51, 120)))
        p.drawText(QRectF(w-160, 8, 150, 14), Qt.AlignRight, "SYS::BOOT_SEQUENCE_v3.0")

        # Bottom edge label — left side
        p.setPen(QPen(QColor(0, 229, 255, 80)))
        p.drawText(QRectF(10, h-18, 200, 14), Qt.AlignLeft, "ROG // STRIX INTELLIGENCE")

        # ════════════════════════════════════════════════
        # LEFT PANEL — decorative vertical line + dots
        # ════════════════════════════════════════════════
        panel_x = 42
        p.setPen(QPen(QColor(255, 0, 51, 50), 1))
        p.drawLine(panel_x, 30, panel_x, h-30)
        # Tick marks along left line
        for ti in range(6):
            ty = 50 + ti * (h - 80) // 6
            tick_w = 8 if ti % 2 == 0 else 4
            p.setPen(QPen(QColor(255, 0, 51, 100 if ti % 2 == 0 else 50), 1))
            p.drawLine(panel_x - tick_w, ty, panel_x, ty)

        # RIGHT vertical line mirror
        p.setPen(QPen(QColor(255, 0, 51, 50), 1))
        p.drawLine(w-panel_x, 30, w-panel_x, h-30)
        for ti in range(6):
            ty = 50 + ti * (h - 80) // 6
            p.setPen(QPen(QColor(255, 0, 51, 100 if ti % 2 == 0 else 50), 1))
            p.drawLine(w-panel_x, ty, w-panel_x + (8 if ti%2==0 else 4), ty)

        # ════════════════════════════════════════════════
        # S ICON SECTION  (top 40% of window)
        # ════════════════════════════════════════════════
        icon_cy = 148   # center Y of the icon area
        sx  = cx + self._s_offset_x
        sy_s = icon_cy + self._s_offset_y

        # Soft red ambient bloom behind everything
        bloom = QRadialGradient(cx, icon_cy, 90)
        bloom.setColorAt(0,   QColor(255, 0, 30, 35))
        bloom.setColorAt(0.6, QColor(255, 0, 30, 12))
        bloom.setColorAt(1,   QColor(0,   0, 0,  0))
        p.setBrush(QBrush(bloom))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(cx-90, icon_cy-90, 180, 180))

        # Rotating dashed outer ring
        a = int(120 + self._pulse * 100)
        pen_r = QPen(QColor(255, 0, 51, a), 2)
        pen_r.setDashPattern([8, 5])
        p.setPen(pen_r)
        p.save(); p.translate(sx, sy_s); p.rotate(self._angle)
        p.drawEllipse(QRectF(-62, -62, 124, 124))
        p.restore()

        # Counter-rotating fine cyan ring
        pen_c = QPen(QColor(0, 229, 255, int(a * 0.6)), 1)
        pen_c.setDashPattern([3, 6])
        p.setPen(pen_c)
        p.save(); p.translate(sx, sy_s); p.rotate(-self._angle * 1.5)
        p.drawEllipse(QRectF(-44, -44, 88, 88))
        p.restore()

        # Slow gold outer orbit
        pen_g = QPen(QColor(255, 180, 0, int(a * 0.3)), 1)
        pen_g.setDashPattern([2, 10])
        p.setPen(pen_g)
        p.save(); p.translate(sx, sy_s); p.rotate(self._angle * 0.3)
        p.drawEllipse(QRectF(-78, -78, 156, 156))
        p.restore()

        # ── S LETTER — glitch holographic ────────────
        gf = self._glitch_frame if self._glitch_active else 0
        font_s = QFont("Consolas", 34, QFont.Bold)
        p.setFont(font_s)

        off1x = 5 + (random.randint(2,9) if gf else 3)
        off1y = random.randint(-2,2) if gf else 1
        p.setPen(QPen(QColor(255, 0, 180, 85)))
        p.drawText(QRectF(sx-36+off1x, sy_s-30+off1y, 72, 60), Qt.AlignCenter, "S")

        off2x = -(4 + (random.randint(1,7) if gf else 2))
        off2y = random.randint(-3,3) if gf else -1
        p.setPen(QPen(QColor(0, 255, 255, 85)))
        p.drawText(QRectF(sx-36+off2x, sy_s-30+off2y, 72, 60), Qt.AlignCenter, "S")

        off3x = random.randint(-3,3) if gf else 1
        off3y = -(3 + (random.randint(1,5) if gf else 1))
        p.setPen(QPen(QColor(0, 255, 100, 65)))
        p.drawText(QRectF(sx-36+off3x, sy_s-30+off3y, 72, 60), Qt.AlignCenter, "S")

        p.setPen(QPen(QColor(255, 0, 51, 195)))
        p.drawText(QRectF(sx-36, sy_s-30, 72, 60), Qt.AlignCenter, "S")
        p.setPen(QPen(QColor(255, 255, 255, 235)))
        p.drawText(QRectF(sx-36, sy_s-30, 72, 60), Qt.AlignCenter, "S")

        # Scanline bands through S
        nb = 7 if not gf else random.randint(5, 14)
        s_rect_y = sy_s - 30; s_rect_h = 60
        band_cols = [QColor(0,255,255,50), QColor(255,0,255,45),
                     QColor(0,255,100,40), QColor(255,255,0,40),
                     QColor(255,80,255,45), QColor(0,200,255,45), QColor(255,100,0,40)]
        for bi in range(nb):
            by_ = s_rect_y + int(bi * s_rect_h / nb)
            bh_ = max(1, int(s_rect_h / nb) - 1)
            bs_ = random.randint(-9,9) if gf else (bi%3-1)*2
            p.setOpacity(0.4)
            p.fillRect(int(sx-26+bs_), by_, 52, bh_, band_cols[bi%len(band_cols)])
        p.setOpacity(1.0)

        # Glitch pixel rows
        if self._glitch_active and random.random() < 0.6:
            for _ in range(random.randint(1,4)):
                ry = sy_s-30+random.randint(0,60)
                rx = random.randint(-16,16)
                rh = random.randint(1,4)
                rc = random.choice([QColor(0,255,255,160),QColor(255,0,255,150),
                                    QColor(255,255,255,180),QColor(0,255,100,140)])
                p.setOpacity(0.7)
                p.fillRect(sx-26+rx, ry, 52, rh, rc)
                p.setOpacity(1.0)

        # ── Title text ────────────────────────────────
        tx = self._s_offset_x // 2 if self._glitch_active else 0
        p.setFont(QFont("Consolas", 18, QFont.Bold))
        p.setPen(QPen(QColor(ROG)))
        p.drawText(QRectF(tx, icon_cy + 72, w, 30), Qt.AlignCenter, "S . T . R . I . X")

        # Subtitle with letter-spacing feel
        p.setFont(QFont("Consolas", 7))
        p.setPen(QPen(QColor(0, 150, 200, 160)))
        p.drawText(QRectF(0, icon_cy + 100, w, 18), Qt.AlignCenter,
                   "STRATEGIC  TACTICAL  RESPONSE  INTELLIGENCE  XSYSTEM")

        # Thin separator line under title
        sep_y = icon_cy + 122
        sep_grad = QLinearGradient(80, 0, w-80, 0)
        sep_grad.setColorAt(0,   QColor(255, 0, 51, 0))
        sep_grad.setColorAt(0.2, QColor(255, 0, 51, 180))
        sep_grad.setColorAt(0.8, QColor(255, 0, 51, 180))
        sep_grad.setColorAt(1,   QColor(255, 0, 51, 0))
        p.setPen(QPen(QBrush(sep_grad), 1))
        p.drawLine(80, sep_y, w-80, sep_y)
        # Center diamond on separator
        dm = 4
        p.setBrush(QBrush(QColor(255, 0, 51, 200)))
        p.setPen(Qt.NoPen)
        from PySide6.QtGui import QPolygon; from PySide6.QtCore import QPoint
        p.drawPolygon(QPolygon([QPoint(cx,sep_y-dm),QPoint(cx+dm,sep_y),
                                QPoint(cx,sep_y+dm),QPoint(cx-dm,sep_y)]))

        # ════════════════════════════════════════════════
        # BOOT LOG SECTION
        # ════════════════════════════════════════════════
        log_top = sep_y + 14
        log_x   = 70

        # Log background panel
        log_h = 5 * 20 + 10
        p.setBrush(QBrush(QColor(10, 14, 24, 160)))
        p.setPen(QPen(QColor(255, 0, 51, 30), 1))
        p.drawRect(log_x - 8, log_top - 4, w - 2*(log_x-8), log_h)

        # Label
        p.setFont(QFont("Consolas", 7))
        p.setPen(QPen(QColor(255, 0, 51, 100)))
        p.drawText(QRectF(log_x, log_top - 16, 120, 14), Qt.AlignLeft, "[ BOOT LOG ]")

        # Lines
        p.setFont(QFont("Consolas", 9))
        y = log_top + 2
        for i, line in enumerate(self._lines):
            lx_off = random.randint(-2,2) if self._glitch_active else 0
            is_last = (i == len(self._lines) - 1)
            if line == "STRIX ONLINE.":
                lc = QColor(255, 215, 0)     # gold — final line
            elif is_last:
                lc = QColor(0, 255, 136)     # green — active line
            else:
                lc = QColor(0, 160, 200, 180) # dim cyan — past lines

            # Prompt arrow — color matches line
            p.setPen(QPen(QColor(255, 0, 51, 160)))
            p.drawText(QRectF(log_x+lx_off, y, 18, 18), Qt.AlignLeft, "›")
            p.setPen(QPen(lc))
            p.drawText(QRectF(log_x+18+lx_off, y, w-log_x-26, 18), Qt.AlignLeft, line)
            y += 20

        # ════════════════════════════════════════════════
        # BAR SECTION — full redesign
        # ════════════════════════════════════════════════
        bar_section_y = log_top + log_h + 10

        # ── Section header row ──────────────────────────
        pct = int(self._bar * 100)
        p.setFont(QFont("Consolas", 7))
        p.setPen(QPen(QColor(255, 0, 51, 150)))
        p.drawText(QRectF(log_x, bar_section_y, 120, 14), Qt.AlignLeft, "LOADING...")
        # Percentage — right aligned, bright
        p.setFont(QFont("Consolas", 11, QFont.Bold))
        p.setPen(QPen(QColor(255, 255, 255, 220)))
        p.drawText(QRectF(0, bar_section_y - 2, w - log_x, 16), Qt.AlignRight, f"{pct}%")

        bar_top = bar_section_y + 18
        bar_x   = log_x
        bar_w   = w - 2 * log_x
        bar_h   = 14        # taller, more presence

        # ── Outer frame / housing ─────────────────────
        # Shadow beneath bar
        shadow_g = QLinearGradient(bar_x, bar_top+bar_h, bar_x, bar_top+bar_h+6)
        shadow_g.setColorAt(0, QColor(0,0,0,80)); shadow_g.setColorAt(1, QColor(0,0,0,0))
        p.fillRect(bar_x, bar_top+bar_h, bar_w, 6, shadow_g)

        # Housing outer border
        p.setPen(QPen(QColor(80, 10, 10, 200), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(bar_x - 1, bar_top - 1, bar_w + 2, bar_h + 2)
        # Housing inner subtle border
        p.setPen(QPen(QColor(255, 0, 51, 40), 1))
        p.drawRect(bar_x, bar_top, bar_w, bar_h)

        # Track fill — very dark red
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(20, 3, 3)))
        p.drawRect(bar_x, bar_top, bar_w, bar_h)

        # ── Segment markers (every 10%) ────────────────
        p.setPen(QPen(QColor(0, 0, 0, 120), 1))
        for seg_i in range(1, 10):
            sx_m = bar_x + int(bar_w * seg_i / 10)
            p.drawLine(sx_m, bar_top, sx_m, bar_top + bar_h)
        # Every 25% — brighter tick
        p.setPen(QPen(QColor(0, 0, 0, 200), 1))
        for q in [25, 50, 75]:
            sx_m = bar_x + int(bar_w * q / 100)
            p.drawLine(sx_m, bar_top, sx_m, bar_top + bar_h)

        # ── Filled portion ─────────────────────────────
        filled = int(bar_w * self._bar)
        if filled > 0:
            ph = self._bar_rgb_phase
            pulse_b = int(190 + ph * 65)

            # Main fill gradient — deep red → hot red
            grad = QLinearGradient(bar_x, 0, bar_x + filled, 0)
            grad.setColorAt(0.0,  QColor(80,  0,   0))
            grad.setColorAt(0.3,  QColor(160, 0,   0))
            grad.setColorAt(0.7,  QColor(230, 0,   0))
            grad.setColorAt(0.92, QColor(255, 0,   0))
            grad.setColorAt(1.0,  QColor(pulse_b, 0, 0))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.NoPen)
            p.drawRect(bar_x, bar_top, filled, bar_h)

            # Top highlight strip — bright thin line
            hi_g = QLinearGradient(bar_x, 0, bar_x + filled, 0)
            hi_g.setColorAt(0,   QColor(255, 100, 100, 0))
            hi_g.setColorAt(0.3, QColor(255, 160, 160, 100))
            hi_g.setColorAt(0.9, QColor(255, 200, 200, 180))
            hi_g.setColorAt(1,   QColor(255, 255, 255, 220))
            p.setBrush(QBrush(hi_g))
            p.drawRect(bar_x, bar_top, filled, 2)

            # Bottom shadow strip
            p.setBrush(QBrush(QColor(0, 0, 0, 80)))
            p.drawRect(bar_x, bar_top + bar_h - 2, filled, 2)

            # Scanlines through filled area
            p.setPen(QPen(QColor(0, 0, 0, 45), 1))
            for sl in range(bar_top + 2, bar_top + bar_h - 2, 2):
                p.drawLine(bar_x, sl, bar_x + filled, sl)

            # ── Glitch segments ────────────────────────
            if self._glitch_active or random.random() < 0.10:
                for _ in range(random.randint(2, 5)):
                    sg_x = bar_x + random.randint(0, max(1, filled-16))
                    sg_w = random.randint(3, 18)
                    sg_y = bar_top + random.randint(-2, 2)
                    sg_h = bar_h + random.randint(-2, 3)
                    sg_a = random.randint(100, 200)
                    sg_c = random.choice([
                        QColor(255,0,0,sg_a), QColor(255,40,40,sg_a),
                        QColor(200,0,0,sg_a), QColor(255,255,255,int(sg_a*0.35)),
                    ])
                    p.setBrush(QBrush(sg_c))
                    p.setPen(Qt.NoPen)
                    p.drawRect(min(sg_x, bar_x+filled), sg_y,
                               min(sg_w, bar_x+filled-sg_x), sg_h)

            # ── Hot leading edge ───────────────────────
            ew = 12
            ex = bar_x + filled - ew
            if ex >= bar_x:
                eg = QLinearGradient(ex, 0, ex+ew, 0)
                eg.setColorAt(0,   QColor(255, 0,   0,   0))
                eg.setColorAt(0.4, QColor(255, 60,  60,  140))
                eg.setColorAt(0.75,QColor(255, 200, 200, 220))
                eg.setColorAt(1,   QColor(255, 255, 255, 255))
                p.setBrush(QBrush(eg)); p.setPen(Qt.NoPen)
                p.drawRect(ex, bar_top, ew, bar_h)

            # ── Outer red glow around bar ──────────────
            for gw_, ga_ in [(4, 40), (8, 18), (14, 8)]:
                gg = QLinearGradient(bar_x, bar_top-gw_, bar_x, bar_top+bar_h+gw_)
                gg.setColorAt(0,   QColor(255,0,0,0))
                gg.setColorAt(0.5, QColor(255,0,0,ga_))
                gg.setColorAt(1,   QColor(255,0,0,0))
                p.fillRect(bar_x, bar_top-gw_, filled, bar_h+gw_*2, gg)

        # ── Percentage tick marks below bar ───────────
        tick_y = bar_top + bar_h + 5
        p.setFont(QFont("Consolas", 6))
        for q in [0, 25, 50, 75, 100]:
            tx_ = bar_x + int(bar_w * q / 100)
            p.setPen(QPen(QColor(255, 0, 51, 100), 1))
            p.drawLine(tx_, tick_y, tx_, tick_y + 4)
            p.setPen(QPen(QColor(255, 0, 51, 80)))
            align = Qt.AlignLeft if q == 0 else (Qt.AlignRight if q == 100 else Qt.AlignCenter)
            p.drawText(QRectF(tx_-12, tick_y+5, 24, 12), align, f"{q}%")

        # ════════════════════════════════════════════════
        # GLITCH OVERLAY strips (burst phase)
        # ════════════════════════════════════════════════
        if self._glitch_active and self._glitch_strips:
            p.setClipRect(4, 4, w-8, h-8)
            for (gy, gh, gsh, gc) in self._glitch_strips:
                p.setOpacity(0.50)
                p.fillRect(gsh, gy, w, gh, gc)
                p.fillRect(-gsh, gy+2, w, max(1,gh//2),
                            QColor(255-gc.red(), 255-gc.green(), 255-gc.blue(), 70))
            p.setOpacity(1.0)
            p.setClipping(False)
            if self._glitch_frame % 4 == 0:
                fc = random.choice([QColor(255,0,51,16), QColor(0,229,255,13),
                                    QColor(255,0,255,11), QColor(0,255,136,11)])
                p.fillRect(0, 0, w, h, fc)

        p.end()


# ── Animated HUD ──────────────────────────────────────────────
class HudBg(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._angle = 0.0; self._angle2 = 0.0
        self._pulse = 0.0; self._pdir   = 1
        img_data = base64.b64decode(HUD_B64 + "==")
        self._pix = QPixmap()
        self._pix.loadFromData(img_data)
        t = QTimer(self); t.timeout.connect(self._tick); t.start(30)

    def _tick(self):
        self._angle  = (self._angle  + 0.35) % 360
        self._angle2 = (self._angle2 - 0.18) % 360
        self._pulse += 0.04 * self._pdir
        if self._pulse >= 1 or self._pulse <= 0: self._pdir *= -1
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height(); cx, cy = w//2, h//2
        grad = QRadialGradient(cx, cy, max(w,h)*0.7)
        grad.setColorAt(0, QColor(8,20,45,255))
        grad.setColorAt(1, QColor(5,9,18,255))
        p.fillRect(self.rect(), grad)
        p.setOpacity(0.03)
        pen = QPen(QColor(0,200,255)); pen.setWidth(1); p.setPen(pen)
        for y in range(0, h, 4): p.drawLine(0,y,w,y)
        vig = QRadialGradient(cx,cy,max(w,h)*0.55)
        vig.setColorAt(0,QColor(0,0,0,0)); vig.setColorAt(1,QColor(0,0,0,200))
        p.setOpacity(1.0); p.fillRect(self.rect(),vig); p.end()


# ── Logo ──────────────────────────────────────────────────────
class Logo(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(52,52)
        self._a = 0.0
        t = QTimer(self); t.timeout.connect(self._tick); t.start(30)

    def _tick(self):
        self._a = (self._a+1.2)%360; self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        cx,cy,r = 26,26,22
        p.save(); p.translate(cx,cy); p.rotate(self._a)
        pen=QPen(QColor(ROG),2); pen.setDashPattern([3,3]); p.setPen(pen)
        p.drawEllipse(QRectF(-r,-r,r*2,r*2)); p.restore()
        p.save(); p.translate(cx,cy); p.rotate(-self._a*1.5)
        pen2=QPen(QColor(CYAN),1); pen2.setDashPattern([2,5]); p.setPen(pen2)
        p.drawEllipse(QRectF(-r*.65,-r*.65,r*1.3,r*1.3)); p.restore()
        g=QRadialGradient(cx,cy,10)
        g.setColorAt(0,QColor(255,0,51,220)); g.setColorAt(1,QColor(200,0,40,0))
        p.setBrush(QBrush(g)); p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(cx-10,cy-10,20,20))
        p.setPen(QPen(QColor("#ffffff"),2))
        p.setFont(QFont("Consolas",11,QFont.Bold))
        p.drawText(QRectF(0,0,52,52),Qt.AlignCenter,"S"); p.end()


# ── Wave ──────────────────────────────────────────────────────
class Wave(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.active = False; self._ph = 0.0
        t=QTimer(self); t.timeout.connect(self._tick); t.start(35)

    def _tick(self):
        if self.active: self._ph+=0.20; self.update()

    def set_active(self,v): self.active=v; self.update()

    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(),QColor(0,0,0,0))
        w,h=self.width(),self.height(); cy=h//2
        if not self.active:
            p.setPen(QPen(QColor(DIM),1)); p.drawLine(20,cy,w-20,cy)
            p.end(); return
        for amp,spd,col,wid in [(10,1.0,ROG,2),(5,1.7,CYAN,1)]:
            p.setPen(QPen(QColor(col),wid))
            px,py=0,cy
            for x in range(0,w,3):
                y=int(cy+amp*math.sin(x/w*4*math.pi+self._ph*spd))
                if x>0: p.drawLine(px,py,x,y)
                px,py=x,y
        p.end()


# ── Glow line ─────────────────────────────────────────────────
class GlowLine(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent); self.setFixedHeight(2)
    def paintEvent(self,e):
        p=QPainter(self)
        g=QLinearGradient(0,0,self.width(),0)
        g.setColorAt(0,QColor(0,0,0,0)); g.setColorAt(0.3,QColor(ROG))
        g.setColorAt(0.7,QColor(CYAN)); g.setColorAt(1,QColor(0,0,0,0))
        p.fillRect(self.rect(),g); p.end()


# ── Typing indicator ──────────────────────────────────────────
class TypingIndicator(QWidget):
    """Animated 3-dot typing indicator shown while model is thinking."""
    def __init__(self, model_name: str = "STRIX", parent=None):
        super().__init__(parent)
        self.model_name = model_name
        self._dot = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(400)
        self.setFixedHeight(40)

    def _tick(self):
        self._dot = (self._dot + 1) % 4
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(0,0,0,0))
        # Model name label
        p.setPen(QPen(QColor(ROG)))
        p.setFont(QFont("Consolas", 8, QFont.Bold))
        p.drawText(16, 14, self.model_name)
        # Dots
        for i in range(3):
            alpha = 255 if i < self._dot else 60
            col = QColor(0, 229, 255, alpha)
            p.setBrush(QBrush(col)); p.setPen(Qt.NoPen)
            p.drawEllipse(16 + i*14, 20, 8, 8)
        p.end()


# ── Chat bubble ───────────────────────────────────────────────
class ChatBubble(QWidget):
    def __init__(self, sender: str, text: str, is_strix: bool,
                 model: str = "", parent=None):
        super().__init__(parent)
        self._full_text = text
        self._model     = model
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        col = QVBoxLayout(); col.setSpacing(4)
        ts  = datetime.now().strftime("%H:%M")

        if is_strix:
            # ── Name row with model badge ─────────────────
            name_row = QHBoxLayout()
            name_lbl = QLabel("STRIX")
            name_lbl.setStyleSheet(
                f"color:{ROG}; font-size:9px; font-weight:bold;"
                f" letter-spacing:2px; background:transparent;")
            name_row.addWidget(name_lbl)

            # Model badge
            if model:
                badge_col = model_badge_color(model)
                badge_txt = model_short_name(model)
                badge = QLabel(f" {badge_txt} ")
                badge.setStyleSheet(f"""
                    QLabel {{
                        background: {badge_col}33;
                        color: {badge_col};
                        border: 1px solid {badge_col};
                        border-radius: 3px;
                        font-size: 7px;
                        font-weight: bold;
                        letter-spacing: 1px;
                        padding: 1px 4px;
                    }}
                """)
                name_row.addWidget(badge)

            ts_lbl = QLabel(ts)
            ts_lbl.setStyleSheet(f"color:{TDIM}; font-size:8px; background:transparent;")
            name_row.addWidget(ts_lbl)
            name_row.addStretch()
            col.addLayout(name_row)

            # ── Message content ───────────────────────────
            segments = detect_code_blocks(text)
            for seg in segments:
                if seg["type"] == "code":
                    col.addWidget(self._make_code_block(seg["content"], seg["lang"]))
                else:
                    txt = clean_text(seg["content"]).strip()
                    if txt:
                        col.addWidget(self._make_text_label(txt, is_strix=True))

            col_wrap = QWidget()
            col_wrap.setMaximumWidth(680)
            col_wrap.setLayout(col)
            layout.addWidget(col_wrap)
            layout.addStretch()

            # Copy button
            copy_btn = self._small_btn("COPY", self._copy_all)
            layout.addWidget(copy_btn, 0, Qt.AlignTop)

        else:
            # YOU bubble — right-aligned
            name_row = QHBoxLayout()
            name_row.addStretch()
            ts_lbl = QLabel(ts)
            ts_lbl.setStyleSheet(
                f"color:{TDIM}; font-size:8px; background:transparent;")
            name_lbl = QLabel("YOU")
            name_lbl.setStyleSheet(
                f"color:{GOLD}; font-size:9px; font-weight:bold;"
                f" letter-spacing:2px; background:transparent;")
            name_row.addWidget(ts_lbl)
            name_row.addWidget(name_lbl)
            col.addLayout(name_row)

            msg_lbl = self._make_text_label(text, is_strix=False)
            msg_lbl.setMaximumWidth(600)
            col.addWidget(msg_lbl, 0, Qt.AlignRight)
            col.setAlignment(Qt.AlignRight)

            layout.setAlignment(Qt.AlignRight)
            layout.addStretch(1)
            layout.addLayout(col)

    def _make_text_label(self, txt: str, is_strix: bool) -> QLabel:
        lbl = QLabel(txt)
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.PlainText)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # Expanding width so long words like "multiplication" always wrap,
        # never overflow the bubble
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        if is_strix:
            lbl.setMaximumWidth(660)
            lbl.setMinimumWidth(120)
            # Color bubble based on which model answered
            m = (self._model or "").lower()
            if "qwen" in m or "coder" in m:
                bg  = "rgba(0, 40, 15, 230)"
                bl  = "#00cc44"
                bt  = "rgba(0,204,68,55)"
                bx  = "rgba(0,204,68,20)"
            elif "llama" in m:
                bg  = "rgba(25, 5, 50, 230)"
                bl  = "#aa44ff"
                bt  = "rgba(170,68,255,55)"
                bx  = "rgba(170,68,255,20)"
            elif "tool" in m:
                bg  = "rgba(0, 35, 40, 230)"
                bl  = "#00e5ff"
                bt  = "rgba(0,229,255,55)"
                bx  = "rgba(0,229,255,20)"
            else:
                # phi3 / default — ROG red
                bg  = "rgba(0, 25, 50, 230)"
                bl  = ROG
                bt  = "rgba(255,0,51,55)"
                bx  = "rgba(0,229,255,20)"
            lbl.setStyleSheet(f"""
                QLabel {{
                    background: {bg};
                    color: {TEXT};
                    border-left: 2px solid {bl};
                    border-top: 1px solid {bt};
                    border-right: 1px solid {bx};
                    border-bottom: 1px solid {bx};
                    border-radius: 0px 10px 10px 10px;
                    padding: 10px 16px;
                    font-size: 12px;
                    font-family: Consolas;
                    line-height: 1.6;
                }}
            """)
        else:
            lbl.setMaximumWidth(560)
            lbl.setMinimumWidth(80)
            lbl.setStyleSheet(f"""
                QLabel {{
                    background: rgba(50, 32, 0, 225);
                    color: #ffffff;
                    border-right: 2px solid {GOLD};
                    border-top: 1px solid rgba(255,215,0,70);
                    border-left: 1px solid rgba(255,215,0,25);
                    border-bottom: 1px solid rgba(255,215,0,25);
                    border-radius: 10px 0px 10px 10px;
                    padding: 10px 16px;
                    font-size: 12px;
                    font-family: Consolas;
                }}
            """)
        return lbl

    def _make_code_block(self, code: str, lang: str) -> QFrame:
        import html as _html
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: #0a0e1a;
                border: 1px solid {ROG};
                border-left: 3px solid {ROG};
                border-radius: 6px;
            }}
        """)
        frame.setMaximumWidth(900)
        vl = QVBoxLayout(frame)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # ── Top bar ───────────────────────────────────────
        bar = QWidget()
        bar.setFixedHeight(28)
        bar.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 rgba(255,0,51,50), stop:1 rgba(0,0,0,0));"
            f"border-radius: 6px 6px 0 0;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(10, 0, 8, 0)

        # Language pill
        lang_name = lang.upper() if lang else "CODE"
        lang_lbl = QLabel(lang_name)
        lang_lbl.setStyleSheet(
            f"color:{ROG}; font-size:9px; font-weight:bold;"
            f" letter-spacing:3px; background:transparent;")

        # Line count
        n_lines = code.count("\n") + 1
        lines_lbl = QLabel(f"{n_lines} LINES")
        lines_lbl.setStyleSheet(
            f"color:{TDIM}; font-size:8px; letter-spacing:1px; background:transparent;")

        copy_btn = QPushButton("⎘ COPY")
        copy_btn.setFixedSize(52, 18)
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color:{CYAN};
                border: 1px solid {CYAN2}; border-radius: 3px;
                font-size: 8px; letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: {CYAN}; color: #000;
            }}
        """)
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(code))
        bl.addWidget(lang_lbl)
        bl.addSpacing(10)
        bl.addWidget(lines_lbl)
        bl.addStretch()
        bl.addWidget(copy_btn)
        vl.addWidget(bar)

        # ── Thin separator ────────────────────────────────
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: rgba(255,0,51,40);")
        vl.addWidget(sep)

        # ── Code body with syntax-highlight colors ────────
        # Simple keyword highlighter using HTML spans
        def highlight(code_str: str, language: str) -> str:
            safe = _html.escape(code_str)
            if language in ("python", "py"):
                import re as _re
                # keywords
                kws = (r'\b(def|class|import|from|return|if|else|elif|for|while|'
                       r'in|not|and|or|True|False|None|try|except|finally|with|'
                       r'as|pass|break|continue|lambda|yield|async|await|raise|'
                       r'global|nonlocal|del|is)\b')
                safe = _re.sub(kws,
                    r'<span style="color:#ff7b72;">\1</span>', safe)
                # strings
                safe = _re.sub(r'(&#x27;[^&#]*&#x27;|&quot;[^&]*&quot;)',
                    r'<span style="color:#a5d6ff;">\1</span>', safe)
                # comments
                safe = _re.sub(r'(#[^\n]*)',
                    r'<span style="color:#6e7681;">\1</span>', safe)
                # numbers
                safe = _re.sub(r'\b(\d+\.?\d*)\b',
                    r'<span style="color:#f2cc60;">\1</span>', safe)
                # builtins/functions
                safe = _re.sub(r'\b(print|len|range|str|int|float|list|dict|'
                               r'set|tuple|type|open|super|self)\b',
                    r'<span style="color:#d2a8ff;">\1</span>', safe)
            elif language in ("javascript", "js", "typescript", "ts"):
                import re as _re
                kws = (r'\b(const|let|var|function|return|if|else|for|while|'
                       r'class|import|export|from|async|await|new|this|typeof|'
                       r'true|false|null|undefined|try|catch|finally|throw|'
                       r'switch|case|break|continue|default)\b')
                safe = _re.sub(kws,
                    r'<span style="color:#ff7b72;">\1</span>', safe)
                safe = _re.sub(r'(&#x27;[^&#]*&#x27;|&quot;[^&]*&quot;|`[^`]*`)',
                    r'<span style="color:#a5d6ff;">\1</span>', safe)
                safe = _re.sub(r'(//[^\n]*)',
                    r'<span style="color:#6e7681;">\1</span>', safe)
                safe = _re.sub(r'\b(\d+\.?\d*)\b',
                    r'<span style="color:#f2cc60;">\1</span>', safe)
            # Add line numbers
            html_lines = safe.split("\n")
            numbered = []
            for i, line in enumerate(html_lines, 1):
                num = f'<span style="color:#3a6080;user-select:none;">{i:3d}  </span>'
                numbered.append(num + line)
            return "\n".join(numbered)

        highlighted = highlight(code, lang.lower() if lang else "")
        code_lbl = QLabel()
        code_lbl.setTextFormat(Qt.RichText)
        code_lbl.setText(
            f'<pre style="font-family:Consolas,monospace;font-size:11px;'
            f'line-height:1.6;margin:0;padding:12px 14px;">{highlighted}</pre>')
        code_lbl.setWordWrap(False)
        code_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        code_lbl.setStyleSheet(
            "QLabel { color:#e6edf3; background:transparent; border:none; }")
        vl.addWidget(code_lbl)
        return frame

    def _small_btn(self, label, slot) -> QPushButton:
        b = QPushButton(label)
        b.setFixedSize(44, 20)
        b.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0,40,80,160); color:{TDIM};
                border:1px solid {DIM}; border-radius:4px;
                font-size:7px; letter-spacing:1px;
            }}
            QPushButton:hover {{ color:{CYAN}; border-color:{CYAN}; }}
        """)
        b.clicked.connect(slot)
        return b

    def _copy_all(self):
        QApplication.clipboard().setText(self._full_text)


# ── Streaming bubble ──────────────────────────────────────────
class StreamingBubble(QWidget):
    def __init__(self, model: str = "", parent=None):
        super().__init__(parent)
        self._text  = ""
        self._model = model
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        col = QVBoxLayout(); col.setSpacing(4)

        name_row = QHBoxLayout()
        name_lbl = QLabel("STRIX")
        name_lbl.setStyleSheet(
            f"color:{ROG}; font-size:9px; font-weight:bold;"
            f" letter-spacing:2px; background:transparent;")
        name_row.addWidget(name_lbl)

        if model:
            badge_col = model_badge_color(model)
            badge     = QLabel(f" {model_short_name(model)} ")
            badge.setStyleSheet(f"""
                QLabel {{
                    background: {badge_col}33; color:{badge_col};
                    border:1px solid {badge_col}; border-radius:3px;
                    font-size:7px; font-weight:bold;
                    padding:1px 4px; letter-spacing:1px;
                }}
            """)
            name_row.addWidget(badge)
        name_row.addStretch()
        col.addLayout(name_row)

        self._lbl = GlitchLabel()
        self._lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self._lbl.setStyleSheet(f"""
            QLabel {{
                background: rgba(0, 50, 80, 210); color:{TEXT};
                border: 1px solid {CYAN2};
                border-radius: 0px 14px 14px 14px;
                padding: 10px 16px; font-size: 12px; font-family: Consolas;
                line-height: 1.6;
            }}
        """)
        col.addWidget(self._lbl)
        layout.addLayout(col)
        layout.addStretch()

    def append(self, token: str):
        self._text += token
        display = clean_text(self._text)
        trimmed = display[-1000:] if len(display) > 1000 else display
        self._lbl.append_target(token)

    def full_text(self) -> str:
        return self._text

    def get_model(self) -> str:
        return self._model


# ── Glitch typing animation ───────────────────────────────────
GLITCH_CHARS = "!<>-_\\/[]{}=+*^?#$%&~@#01"

class GlitchLabel(QLabel):
    """
    Cyber scanline reveal — characters appear with glitch noise.
    Stays in RichText mode always to avoid re-layout flicker.
    Timer stays alive as long as target keeps growing (streaming).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._target   = ""
        self._revealed = 0
        self._frame    = 0
        self._timer    = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setTextFormat(Qt.RichText)
        self.setWordWrap(True)

    def set_target(self, text: str):
        self._target   = text
        self._revealed = 0
        self._frame    = 0
        if not self._timer.isActive():
            self._timer.start(30)

    def append_target(self, extra: str):
        self._target += extra
        if not self._timer.isActive():
            self._timer.start(30)

    def _tick(self):
        import random, html as _h
        self._frame += 1
        gap = len(self._target) - self._revealed

        if gap <= 0:
            # Done — show plain final text and stop
            safe = _h.escape(self._target)
            self.setText(f'<span style="white-space:pre-wrap;">{safe}</span>')
            self._timer.stop()
            return

        # Adaptive speed based on how far behind
        if gap > 120: speed = 6
        elif gap > 60: speed = 3
        elif gap > 20: speed = 2
        else: speed = 1

        self._revealed = min(self._revealed + speed, len(self._target))

        revealed_safe = _h.escape(self._target[:self._revealed])
        remaining     = len(self._target) - self._revealed
        glitch_len    = min(4, remaining)

        if self._frame % 5 < 2:   gc = "#ff0033"
        elif self._frame % 5 < 4: gc = "#00e5ff"
        else:                      gc = "#ffd700"

        glitch_safe = _h.escape(
            "".join(random.choice(GLITCH_CHARS) for _ in range(glitch_len))
        )

        if self._frame % 10 == 0 and remaining > 3:
            fc = random.choice(["#ff0033","#00e5ff","#00ff88"])
            html = (f'<span style="color:{fc};white-space:pre-wrap;">{revealed_safe}</span>'
                    f'<span style="color:{gc};">{glitch_safe}</span>')
        else:
            html = (f'<span style="white-space:pre-wrap;">{revealed_safe}</span>'
                    f'<span style="color:{gc};">{glitch_safe}</span>')

        self.setText(html)



# ── Arc Reactor — ROG HUD behind chat ────────────────────────
class ArcReactor(QWidget):
    """
    ROG-themed arc reactor. Matches GUI palette exactly:
    - Background: deep navy #050912
    - Primary:    ROG red   #ff0033
    - Secondary:  CYAN      #00e5ff
    - Accent:     GOLD      #ffd700
    - Trace:      teal      #00ff88

    Idle: slow dim rotation.
    Speaking: fast bright spin, scan sweep, energy burst.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # angles for each ring
        self._a  = [0.0, 0.0, 0.0, 0.0, 0.0]
        self._pulse  = 0.0
        self._pdir   = 1
        self._scan   = 0.0
        self._energy = 0.25     # 0 = idle  1 = speaking
        self._speaking = False
        self._seg_flash = 0     # cycles gold segments
        t = QTimer(self); t.timeout.connect(self._tick); t.start(20)

    def set_speaking(self, v: bool):
        self._speaking = v

    def _tick(self):
        s = 2.6 if self._speaking else 0.45
        self._a[0] = (self._a[0] + s       ) % 360
        self._a[1] = (self._a[1] - s * 0.6 ) % 360
        self._a[2] = (self._a[2] + s * 1.2 ) % 360
        self._a[3] = (self._a[3] - s * 0.35) % 360
        self._a[4] = (self._a[4] + s * 1.8 ) % 360
        self._pulse += 0.032 * self._pdir
        if self._pulse >= 1.0 or self._pulse <= 0.0: self._pdir *= -1
        self._scan = (self._scan + (0.010 if self._speaking else 0.004)) % 1.0
        self._seg_flash = (self._seg_flash + 1) % 48
        tgt = 1.0 if self._speaking else 0.22
        self._energy += (tgt - self._energy) * 0.08
        self.update()

    def paintEvent(self, ev):
        import math as m
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h   = self.width(), self.height()
        cx, cy = w // 2, h // 2
        R  = min(w, h) * 0.43
        en = self._energy
        pu = self._pulse

        def alpha(base, scale=1.0):
            return min(255, int(base + en * 200 * scale + pu * 30))

        # ═══════════════════════════════════════════════
        # 1. SUBTLE GRID — matches GUI bg scanlines
        # ═══════════════════════════════════════════════
        p.setPen(QPen(QColor(0, 100, 160, int(4 + en * 12)), 1))
        step = 28
        for gy in range(0, h + step, step):
            p.drawLine(0, gy, w, gy)
        for gx in range(0, w + step, step):
            p.drawLine(gx, 0, gx, h)

        # ═══════════════════════════════════════════════
        # 2. OUTER GLOW BLOOM
        # ═══════════════════════════════════════════════
        bloom = QRadialGradient(cx, cy, R * 1.25)
        bloom.setColorAt(0,   QColor(255, 0, 51,   int(14 * en + 3)))
        bloom.setColorAt(0.4, QColor(0,  229, 255,  int(10 * en + 2)))
        bloom.setColorAt(1.0, QColor(0,  0,   0,   0))
        p.setBrush(QBrush(bloom)); p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(cx-R*1.25, cy-R*1.25, R*2.5, R*2.5))

        # ═══════════════════════════════════════════════
        # 3. RING 1 — Outermost dashed ring (ROG red)
        #    with 4 crosshair notches + 48 tick marks
        # ═══════════════════════════════════════════════
        p.save(); p.translate(cx, cy); p.rotate(self._a[0])
        a1 = alpha(40, 0.7)
        # Main ring
        pen1 = QPen(QColor(255, 0, 51, a1), 1)
        pen1.setDashPattern([10, 6])
        p.setPen(pen1); p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(-R, -R, R*2, R*2))
        # Tick marks
        for i in range(48):
            ar   = m.radians(i * 7.5)
            tl   = 11 if i % 4 == 0 else (6 if i % 2 == 0 else 3)
            ta   = a1 if i % 4 == 0 else int(a1 * 0.5)
            p.setPen(QPen(QColor(255, 0, 51, ta), 1))
            p.drawLine(int((R - tl)*m.cos(ar)), int((R - tl)*m.sin(ar)),
                       int(R*m.cos(ar)),        int(R*m.sin(ar)))
        # 4 crosshair spokes at N/E/S/W
        p.setPen(QPen(QColor(255, 0, 51, int(a1 * 0.9)), 2))
        for ang in [0, 90, 180, 270]:
            ar = m.radians(ang)
            p.drawLine(int(R*0.86*m.cos(ar)), int(R*0.86*m.sin(ar)),
                       int(R*1.14*m.cos(ar)), int(R*1.14*m.sin(ar)))
        # Small diamonds at 45° positions
        for ang in [45, 135, 225, 315]:
            ar = m.radians(ang)
            dx, dy = R*m.cos(ar), R*m.sin(ar)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(255, 0, 51, int(a1 * 0.8))))
            diamond = [QPoint(int(dx), int(dy - 5)),
                       QPoint(int(dx + 4), int(dy)),
                       QPoint(int(dx), int(dy + 5)),
                       QPoint(int(dx - 4), int(dy))]
            from PySide6.QtGui import QPolygon
            p.drawPolygon(QPolygon(diamond))
        p.restore()

        # ═══════════════════════════════════════════════
        # 4. RING 2 — Gold segmented energy ring (16 blocks)
        # ═══════════════════════════════════════════════
        R2  = R * 0.84
        p.save(); p.translate(cx, cy); p.rotate(self._a[1])
        for i in range(16):
            # Some segments flash brighter
            bright = (i * 5 + self._seg_flash) % 16 < int(4 + en * 8)
            sa = int(alpha(50, 0.65) * (1.4 if bright else 0.7))
            p.setPen(QPen(QColor(255, 215, 0, min(255, sa)), 4))
            start = int((i * 22.5 + 2.5) * 16)
            span  = int(17 * 16)
            p.drawArc(QRectF(-R2, -R2, R2*2, R2*2), start, span)
        # thin inner dashed
        pd = QPen(QColor(255, 215, 0, int(alpha(20, 0.3))), 1)
        pd.setDashPattern([3, 9])
        p.setPen(pd)
        p.drawEllipse(QRectF(-R2*0.92, -R2*0.92, R2*1.84, R2*1.84))
        p.restore()

        # ═══════════════════════════════════════════════
        # 5. RING 3 — Cyan chevron / arrow ring
        # ═══════════════════════════════════════════════
        R3 = R * 0.68
        p.save(); p.translate(cx, cy); p.rotate(self._a[2])
        a3 = alpha(45, 0.75)
        p.setPen(QPen(QColor(0, 229, 255, a3), 1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(-R3, -R3, R3*2, R3*2))
        # 8 chevron arrows around the ring
        for i in range(8):
            base = m.radians(i * 45)
            ca = int(a3 * (1.0 if i % 2 == 0 else 0.55))
            p.setPen(QPen(QColor(0, 229, 255, ca), 1))
            # draw two >> chevrons outward
            for off in [0.0, 0.13]:
                tip = base + off + 0.11
                top = base + off - 0.09
                bot = base + off + 0.30
                xt,yt = R3*m.cos(tip),      R3*m.sin(tip)
                xp,yp = R3*0.86*m.cos(top), R3*0.86*m.sin(top)
                xb,yb = R3*0.86*m.cos(bot), R3*0.86*m.sin(bot)
                p.drawLine(int(xp),int(yp),int(xt),int(yt))
                p.drawLine(int(xt),int(yt),int(xb),int(yb))
        p.restore()

        # ═══════════════════════════════════════════════
        # 6. RING 4 — Teal circuit trace ring with nodes
        # ═══════════════════════════════════════════════
        R4 = R * 0.53
        p.save(); p.translate(cx, cy); p.rotate(self._a[3])
        a4 = alpha(35, 0.6)
        p.setPen(QPen(QColor(0, 255, 136, a4), 1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(-R4, -R4, R4*2, R4*2))
        for i in range(12):
            ar = m.radians(i * 30)
            nx, ny = R4*m.cos(ar), R4*m.sin(ar)
            is_major = i % 3 == 0
            na = int(a4 * (1.2 if is_major else 0.45))
            p.setBrush(QBrush(QColor(0, 255, 136, min(255, na))))
            p.setPen(Qt.NoPen)
            nr = 4 if is_major else 2
            p.drawEllipse(QRectF(nx-nr, ny-nr, nr*2, nr*2))
            if is_major:
                p.setPen(QPen(QColor(0, 255, 136, int(na * 0.55)), 1))
                p.drawLine(int(nx), int(ny),
                           int((R4+14)*m.cos(ar)), int((R4+14)*m.sin(ar)))
                # small square marker at trace end
                ex, ey = (R4+14)*m.cos(ar), (R4+14)*m.sin(ar)
                p.setBrush(QBrush(QColor(0, 255, 136, int(na * 0.4))))
                p.drawRect(QRectF(ex-2, ey-2, 4, 4))
        p.restore()

        # ═══════════════════════════════════════════════
        # 7. SCAN SWEEP — radar-style cone (matches CYAN)
        # ═══════════════════════════════════════════════
        import math as m2
        sweep_deg = self._scan * 360
        sweep_a   = int(18 + en * 70)
        p.save(); p.translate(cx, cy)
        grad_s = QConicalGradient(0, 0, sweep_deg)
        grad_s.setColorAt(0.00, QColor(0, 229, 255, sweep_a))
        grad_s.setColorAt(0.06, QColor(0, 229, 255, int(sweep_a * 0.4)))
        grad_s.setColorAt(0.12, QColor(0, 0, 0, 0))
        grad_s.setColorAt(1.00, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(grad_s)); p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(-R*0.96, -R*0.96, R*1.92, R*1.92))
        p.restore()

        # ═══════════════════════════════════════════════
        # 8. INNER RING 5 — fast spinning ROG micro-ring
        # ═══════════════════════════════════════════════
        R5 = R * 0.38
        p.save(); p.translate(cx, cy); p.rotate(self._a[4])
        a5 = alpha(30, 0.5)
        pen5 = QPen(QColor(255, 0, 51, a5), 1)
        pen5.setDashPattern([3, 3])
        p.setPen(pen5); p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(-R5, -R5, R5*2, R5*2))
        # 4 small brackets on inner ring
        for ang in [0, 90, 180, 270]:
            ar = m2.radians(ang)
            bx, by = R5*m2.cos(ar), R5*m2.sin(ar)
            nx, ny = m2.cos(ar + m2.pi/2), m2.sin(ar + m2.pi/2)
            p.setPen(QPen(QColor(255, 0, 51, int(a5 * 0.8)), 1))
            p.drawLine(int(bx - nx*5), int(by - ny*5),
                       int(bx + nx*5), int(by + ny*5))
        p.restore()

        # ═══════════════════════════════════════════════
        # 9. CENTER GLOW + ARC REACTOR CORE
        # ═══════════════════════════════════════════════
        Rc = R * 0.22
        core_glow = QRadialGradient(cx, cy, Rc * 2.2)
        core_glow.setColorAt(0,    QColor(180, 240, 255, int(220*en + 70)))
        core_glow.setColorAt(0.25, QColor(0,   200, 255, int(140*en + 30)))
        core_glow.setColorAt(0.6,  QColor(0,   80,  200, int(40 *en + 8)))
        core_glow.setColorAt(1.0,  QColor(0,   0,   0,   0))
        p.setBrush(QBrush(core_glow)); p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(cx-Rc*2.2, cy-Rc*2.2, Rc*4.4, Rc*4.4))

        # Core circle border
        p.setPen(QPen(QColor(0, 229, 255, int(alpha(80, 0.6))), 1))
        p.setBrush(QBrush(QColor(0, 20, 50, int(180 * en + 40))))
        p.drawEllipse(QRectF(cx-Rc, cy-Rc, Rc*2, Rc*2))

        # Inverted triangle
        tri = Rc * 0.68
        tri_a = int(alpha(120, 0.8))
        pts = []
        for i in range(3):
            ar = m2.radians(-90 + 120*i + 180)
            pts.append(QPoint(int(cx + tri*m2.cos(ar)), int(cy + tri*m2.sin(ar))))
        from PySide6.QtGui import QPolygon
        p.setBrush(QBrush(QColor(0, 140, 255, int(55*en + 10))))
        p.setPen(QPen(QColor(0, 229, 255, tri_a), 1))
        p.drawPolygon(QPolygon(pts))

        # Center dot
        p.setBrush(QBrush(QColor(220, 245, 255, int(200*en + 55))))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(cx-3.5, cy-3.5, 7, 7))

        # ═══════════════════════════════════════════════
        # 10. HUD LABELS — ROG style, matching font
        # ═══════════════════════════════════════════════
        la = int(45 + en * 160)
        p.setFont(QFont("Consolas", 7, QFont.Bold))

        # SIGNAL top with bracket
        p.setPen(QPen(QColor(0, 229, 255, la)))
        p.drawText(QRectF(cx-30, cy-R-22, 60, 13), Qt.AlignCenter, "SIGNAL")
        p.setPen(QPen(QColor(0, 229, 255, int(la * 0.5)), 1))
        p.drawLine(cx-18, int(cy-R-10), cx-18, int(cy-R-5))
        p.drawLine(cx+18, int(cy-R-10), cx+18, int(cy-R-5))

        # ENERGY LEVEL bottom
        p.setPen(QPen(QColor(255, 215, 0, la)))
        p.drawText(QRectF(cx-52, cy+R+7, 104, 13), Qt.AlignCenter, "ENERGY LEVEL")

        # WIFI left (rotated)
        p.save(); p.translate(cx - R - 18, cy)
        p.rotate(-90)
        p.setPen(QPen(QColor(0, 229, 255, la)))
        p.drawText(QRectF(-16, -6, 32, 12), Qt.AlignCenter, "WIFI")
        p.restore()

        # STATUS right
        status = "ACTIVE" if self._speaking else "STANDBY"
        sc = QColor(0, 255, 136, la) if self._speaking else QColor(255, 0, 51, int(la * 0.7))
        p.setPen(QPen(sc))
        p.drawText(QRectF(cx+R+4, cy-6, 55, 12), Qt.AlignLeft, status)

        # Energy % — bottom right of reactor
        pct = int(self._energy * 100)
        p.setPen(QPen(QColor(255, 215, 0, int(la * 0.85))))
        p.setFont(QFont("Consolas", 6))
        p.drawText(QRectF(cx+R*0.5, cy+R*0.72, 42, 11), Qt.AlignLeft, f"{pct:02d}%")

        # ═══════════════════════════════════════════════
        # 11. CORNER HUD CIRCUIT BRACKETS (4 corners)
        # ═══════════════════════════════════════════════
        cl = int(35 + en * 95)
        p.setPen(QPen(QColor(0, 229, 255, cl), 1))
        pad = 6
        for dx, dy in [(-1,-1),(1,-1),(-1,1),(1,1)]:
            bx = cx + dx * (R * 1.04)
            by = cy + dy * (R * 0.80)
            ox, oy = dx * 18, 0
            oy2    = dy * 8
            # horizontal
            p.drawLine(int(bx), int(by), int(bx + ox), int(by))
            # vertical drop
            p.drawLine(int(bx + ox), int(by), int(bx + ox), int(by + oy2))
            # end dot
            p.setBrush(QBrush(QColor(0, 229, 255, cl)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QRectF(bx+ox-2, by+oy2-2, 4, 4))
            p.setPen(QPen(QColor(0, 229, 255, cl), 1))
            # second parallel line (thinner)
            p.setPen(QPen(QColor(0, 229, 255, int(cl*0.4)), 1))
            p.drawLine(int(bx), int(by + dy*4), int(bx + ox*0.6), int(by + dy*4))

        p.end()


# ── Chat area ─────────────────────────────────────────────────
class ChatArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ background:{BG2}; width:5px; border-radius:2px; }}
            QScrollBar::handle:vertical {{ background:{DIM}; border-radius:2px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
        """)
        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(8,14,8,14); self._layout.setSpacing(12)
        self._layout.addStretch()
        self.setWidget(self._container)
        self._typing = None

    def _scroll_bottom(self):
        QTimer.singleShot(50, lambda: self.verticalScrollBar().setValue(
            self.verticalScrollBar().maximum()))

    def add_message(self, sender, text, is_strix, model=""):
        bubble = ChatBubble(sender, text, is_strix, model)
        self._layout.insertWidget(self._layout.count()-1, bubble)
        self._scroll_bottom()
        return bubble

    def _typing_alive(self) -> bool:
        """Check C++ object is still valid before touching it."""
        if not self._typing:
            return False
        try:
            self._typing.isVisible()  # raises RuntimeError if C++ deleted
            return True
        except RuntimeError:
            self._typing = None
            return False

    def show_typing(self, model: str = ""):
        self.hide_typing()
        self._typing = TypingIndicator(model_short_name(model) if model else "STRIX")
        self._layout.insertWidget(self._layout.count()-1, self._typing)
        self._scroll_bottom()

    def hide_typing(self):
        if not self._typing_alive():
            self._typing = None
            return
        try:
            self._layout.removeWidget(self._typing)
            self._typing.deleteLater()
        except RuntimeError:
            pass
        finally:
            self._typing = None

    def add_streaming_bubble(self, model: str = "") -> StreamingBubble:
        self.hide_typing()
        bubble = StreamingBubble(model)
        self._layout.insertWidget(self._layout.count()-1, bubble)
        self._scroll_bottom()
        return bubble

    def replace_streaming_bubble(self, streaming: StreamingBubble, full_text: str):
        idx = self._layout.indexOf(streaming)
        if idx >= 0:
            self._layout.removeWidget(streaming)
            streaming.deleteLater()
            bubble = ChatBubble("STRIX", full_text, True, streaming.get_model())
            self._layout.insertWidget(idx, bubble)
            self._scroll_bottom()


# ── Worker threads ────────────────────────────────────────────
class StreamThread(QThread):
    token       = Signal(str)
    done        = Signal(str)
    model_used  = Signal(str)

    def __init__(self, brain, text):
        super().__init__()
        self.brain  = brain
        self.text   = text
        self._stop  = False

    def stop(self): self._stop = True

    def run(self):
        try:
            result = self.brain.process(self.text, stream=True)
            if hasattr(result, '__iter__') and not isinstance(result, str):
                full = ""
                for token in result:
                    if self._stop: break
                    full += token
                    self.token.emit(token)
                self.done.emit(full)
            else:
                self.done.emit(str(result))
        except Exception as e:
            self.done.emit(f"Error: {e}")


class TTSThread(QThread):
    def __init__(self, tts, text):
        super().__init__()
        self.tts = tts; self.text = text
    def run(self):
        if self.tts and self.tts.available and not self.tts.muted:
            self.tts.speak(tts_clean(self.text), blocking=True)


class PreloadThread(QThread):
    weather_ready = Signal(str)
    def run(self):
        try:
            from api.weather import format_weather
            self.weather_ready.emit(format_weather())
        except Exception as e:
            self.weather_ready.emit(f"Weather: {e}")


class ModelListThread(QThread):
    ready = Signal(list)
    def run(self):
        try:
            from models.llm_interface import list_available_models
            self.ready.emit(list_available_models())
        except Exception:
            self.ready.emit([])


import random

# ── Startup messages — gaming + productive vibe ───────────────
STARTUP_GREETINGS = [
    ("All systems online, Boss. Ready to build something legendary today.", False),
    ("STRIX online. CPU cool, RAM ready. What are we coding today, Boss?", False),
    ("Good to see you again, Boss. Three AI models locked and loaded — let's dominate.", False),
    ("Systems nominal. Models ready. What's the mission today, Boss?", False),
    ("STRIX activated. I've been waiting. What are we building today?", False),
    ("Rise and grind, Boss. STRIX is online and ready to destroy some code.", False),
    ("Back online, Boss. Let's build something the world hasn't seen yet.", False),
    ("STRIX reporting for duty. All models hot, all tools sharp. Let's go.", False),
    # Fallback jokes if pyjokes not installed (True = is a joke)
    ("STRIX online. Why do programmers prefer dark mode? Because light attracts bugs. Ready when you are, Boss.", True),
    ("Systems ready. A bug is just an undocumented feature. What can I build for you, Boss?", True),
    ("Why did the developer quit? They didn't get arrays. Anyway — what are we building today?", True),
    ("99 bugs in the code. Fix one, patch around — 127 bugs. Let's squash some today, Boss.", True),
    ("Why do Java developers wear glasses? Because they don't C sharp. Let's get to work, Boss.", True),
    ("A SQL query walks into a bar and asks two tables — can I join you? Ready when you are.", True),
]

PRODUCTIVITY_TIPS = [
    "Tip of the day — commit your code early and often.",
    "Tip of the day — name your variables like the next developer is a serial killer who knows where you live.",
    "Tip of the day — write tests first. Future you will be grateful.",
    "Tip of the day — the best code is the code you never had to write.",
    "Tip of the day — sleep is the best debugger. Take breaks, Boss.",
    "Tip of the day — read error messages carefully. They usually tell you exactly what is wrong.",
    "Tip of the day — keep your functions small. One function, one job.",
]

# Boot sequence lines — shown one by one before greeting
BOOT_SEQUENCE = [
    "INITIALIZING STRIX CORE...",
    "LOADING AI MODELS — phi3 | llama3.1 | qwen2.5-coder",
    "CONNECTING TO OLLAMA ENGINE...",
    "CALIBRATING NEURAL PATHWAYS...",
    "ALL SYSTEMS NOMINAL. STRIX ONLINE.",
]


def _get_joke() -> str:
    """Get a joke — pyjokes first, fallback to hardcoded."""
    try:
        import pyjokes
        joke = pyjokes.get_joke(language="en", category="neutral")
        return joke
    except ImportError:
        # pyjokes not installed — use hardcoded fallbacks
        fallbacks = [s[0] for s in STARTUP_GREETINGS if s[1]]
        return random.choice(fallbacks)
    except Exception:
        fallbacks = [s[0] for s in STARTUP_GREETINGS if s[1]]
        return random.choice(fallbacks)


def get_startup_message():
    """30% chance of joke, 70% serious + optional tip."""
    if random.random() < 0.3:
        joke = _get_joke()
        # Wrap joke with STRIX intro
        intros = [
            "STRIX online. Quick one for you Boss — ",
            "Systems ready. Here is a joke while we warm up — ",
            "Online and operational. Boss, listen to this — ",
            "STRIX activated. Before we start — ",
        ]
        return random.choice(intros) + joke
    serious = [s[0] for s in STARTUP_GREETINGS if not s[1]]
    msg = random.choice(serious)
    if random.random() < 0.5:
        msg += " " + random.choice(PRODUCTIVITY_TIPS)
    return msg


# ── Background listener — works even when STRIX is closed ─────
class BackgroundWakeListener(QThread):
    """
    Runs as a hidden background process.
    Listens 24/7 for wake words even when STRIX window is closed.
    On wake word detected → opens STRIX window.
    """
    wake = Signal()
    WORDS = [
        "hey strix", "ok strix", "wake up strix", "strix wake up",
        "wake up", "yo strix", "strix open", "open strix",
        "strix", "start strix", "launch strix", "strix activate",
        "activate strix", "hello strix", "hi strix", "strix hello",
        "strix i need you", "strix come online",
    ]

    def __init__(self):
        super().__init__()
        self._active = True

    def stop_loop(self):
        self._active = False

    # Strict wake words — must contain "strix" — no single-word accidents
    WORDS = [
        "hey strix", "ok strix", "wake up strix", "strix wake up",
        "yo strix", "strix open", "open strix",
        "start strix", "launch strix", "strix activate",
        "hello strix", "hi strix", "strix hello",
        "strix i need you", "strix come online",
    ]

    def run(self):
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            # HIGH threshold — ignore ambient noise, fan, TV, etc.
            r.energy_threshold         = 2500
            r.pause_threshold          = 0.6
            r.dynamic_energy_threshold = False   # don't auto-lower threshold
            try:
                with sr.Microphone() as src:
                    r.adjust_for_ambient_noise(src, duration=1.5)
                    # Set floor — never go below 2000
                    r.energy_threshold = max(r.energy_threshold, 2000)
            except Exception:
                pass
            print(f"[BG Wake] Listening (threshold={r.energy_threshold:.0f})...")
            while self._active:
                try:
                    with sr.Microphone() as src:
                        audio = r.listen(src, timeout=5, phrase_time_limit=4)
                    text = r.recognize_google(audio, language="en-IN").lower()
                    # Only print if it contains something useful
                    if len(text) > 2:
                        print(f"[BG Wake] Heard: {text}")
                    # Must explicitly contain "strix"
                    if "strix" in text and any(w in text for w in self.WORDS):
                        print("[BG Wake] Wake word detected!")
                        self.wake.emit()
                except Exception:
                    pass
        except ImportError:
            print("[BG Wake] speech_recognition not installed")


class WakeWordThread(QThread):
    wake    = Signal()
    command = Signal(str)   # direct command — execute immediately

    # Wake words — just to activate listening mode
    WAKE_WORDS = [
        "hey strix", "ok strix", "wake up strix", "strix wake up",
        "yo strix", "open strix", "strix open",
        "start strix", "launch strix", "strix activate", "activate strix",
        "strix are you there", "strix come online", "strix i need you",
        "hello strix", "hi strix", "strix hello",
    ]

    # Pure wake words — trigger WITHOUT requiring "strix" in text
    PURE_WAKE_WORDS = [
        "wake up", "hey strix", "ok strix", "yo strix",
        "strix wake up", "wake up strix",
    ]

    # Action prefixes — execute directly WITHOUT needing "strix" first
    ACTION_PREFIXES = (
        "open ", "play ", "launch ", "start ", "run ",
        "close ", "search for ", "find ", "go to ",
        "create ", "make a ", "make ", "show ",
        "write code", "write a ", "write me ",
        "create a python", "create a javascript", "create a html",
        "create a file", "create a script",
        "locate ", "where is ", "find this ", "find my ",
        "work time", "work mode", "coding time",
        "show anime", "watch anime",
        "shutdown", "shut down", "kill", "kill strix",
    )

    def __init__(self):
        super().__init__()
        self._active        = True
        self._paused        = False
        self._hard_muted    = False   # True while TTS is speaking
        self._music_playing = False   # True while Spotify is playing
        self._noise_floor   = 2500    # calibrated at startup

    def pause(self):          self._paused = True
    def resume(self):         self._paused = False
    def hard_mute(self):      self._hard_muted = True
    def hard_unmute(self):    self._hard_muted = False
    def music_started(self):  self._music_playing = True
    def music_stopped(self):  self._music_playing = False

    def stop_loop(self):
        self._active = False
        self.quit()

    def _is_action_command(self, text: str) -> bool:
        """Returns True if text is a direct command.
        Checks startswith, then strips common filler words and checks again."""
        tl = text.lower().strip()
        # Direct match
        if any(tl.startswith(p) for p in self.ACTION_PREFIXES):
            return True
        # Strip filler words (Google sometimes prepends these)
        for f in ("can you ", "please ", "hey ", "could you ",
                  "i want to ", "i need to ", "strix ", "strix, "):
            if tl.startswith(f):
                rest = tl[len(f):]
                if any(rest.startswith(p) for p in self.ACTION_PREFIXES):
                    return True
        return False

    def run(self):
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            r.energy_threshold         = 2500
            r.pause_threshold          = 0.5
            r.dynamic_energy_threshold = False
            try:
                with sr.Microphone() as src:
                    r.adjust_for_ambient_noise(src, duration=1.0)
                    r.energy_threshold = max(r.energy_threshold, 2000)
                    self._noise_floor  = r.energy_threshold
                    print(f"[Wake] Threshold set to {r.energy_threshold:.0f}")
            except Exception:
                self._noise_floor = 2500

            while self._active:
                if self._paused or self._hard_muted:
                    time.sleep(0.15)
                    continue

                # Music playing — raise threshold so speaker audio can't trigger mic
                if self._music_playing:
                    r.energy_threshold = max(self._noise_floor * 2.5, 5500)
                else:
                    r.energy_threshold = self._noise_floor

                try:
                    with sr.Microphone() as src:
                        plimit = 3 if self._music_playing else 6
                        audio  = r.listen(src, timeout=2, phrase_time_limit=plimit)

                    if not self._active or self._hard_muted:
                        break

                    raw  = r.recognize_google(audio, language="en-IN", show_all=True)
                    text = ""
                    if isinstance(raw, dict) and raw.get("alternative"):
                        alts = raw["alternative"]
                        # Prefer longest transcript — captures full command
                        text = max(
                            (a.get("transcript","") for a in alts),
                            key=lambda t: len(t.split()),
                            default=""
                        ).lower().strip()
                    elif isinstance(raw, str):
                        text = raw.lower().strip()

                    if not text:
                        continue

                    # ── Music self-hearing guard ──────────────────────────────
                    # When music is playing: 4+ word result = song lyric, discard
                    if self._music_playing:
                        words = text.split()
                        if len(words) > 4:
                            continue
                        music_cmds = {
                            "pause", "stop", "skip", "next", "previous", "resume",
                            "unpause", "play", "volume up", "volume down",
                            "louder", "quieter", "mute", "strix",
                            "stop music", "pause music", "stop the music",
                            "pause the song", "stop the song", "hey strix",
                        }
                        if not any(cmd in text for cmd in music_cmds):
                            continue   # music bleed — ignore

                    # ── General self-echo guard ───────────────────────────────
                    # Long audio with no command/wake word = TTS reverb or ambient
                    words    = text.split()
                    has_cmd  = self._is_action_command(text)
                    has_wake = (any(w in text for w in self.PURE_WAKE_WORDS)
                                or "strix" in text)
                    if not has_cmd and not has_wake and len(words) > 6:
                        continue   # TTS echo or ambient — discard

                    if len(text) > 2:
                        print(f"[Wake] Heard: {text}")

                    if has_cmd:
                        print(f"[Wake] Direct command → {text}")
                        self.command.emit(text)
                    elif any(w in text for w in self.PURE_WAKE_WORDS):
                        print(f"[Wake] Wake word → {text}")
                        self.wake.emit()
                    elif "strix" in text and any(w in text for w in self.WAKE_WORDS):
                        print(f"[Wake] Wake word → {text}")
                        self.wake.emit()

                except sr.WaitTimeoutError:
                    pass
                except Exception:
                    pass
        except ImportError:
            print("[Wake] speech_recognition not installed")


# ── Stat card ─────────────────────────────────────────────────
class StatCard(QFrame):
    def __init__(self, icon, label, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"QFrame {{ background:rgba(0,40,80,180); border:1px solid {DIM}; border-radius:8px; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10,7,10,7); lay.setSpacing(1)
        top = QHBoxLayout()
        ico = QLabel(icon); ico.setStyleSheet(f"color:{ROG}; font-size:12px; background:transparent; border:none;")
        lbl = QLabel(label.upper()); lbl.setStyleSheet(f"color:{TDIM}; font-size:8px; letter-spacing:2px; background:transparent; border:none;")
        top.addWidget(ico); top.addWidget(lbl); top.addStretch()
        lay.addLayout(top)
        self.val = QLabel("..."); self.val.setStyleSheet(f"color:{TEXT}; font-size:10px; font-weight:bold; background:transparent; border:none;")
        lay.addWidget(self.val)

    def set_value(self, t): self.val.setText(t)


# ── Main Window ───────────────────────────────────────────────
class StrixWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.brain            = None
        self.tts              = None
        self._stream_thread   = None
        self._tts_threads     = []
        self._streaming_bubble = None
        self._wake_thread     = None
        self._current_model   = "phi3:latest"

        self.setWindowTitle("STRIX — ROG AI")
        self.setMinimumSize(1080, 720)
        self._style()
        self._build()
        self._setup_shortcuts()
        self._restore_window()

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)
        self._tick_clock()

        # Ambient animations — mounted after window is built
        self._corners  = None
        self._particles = None
        QTimer.singleShot(100, self._lazy_load)
        QTimer.singleShot(200, self._mount_overlays)

    def _style(self):
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(BG))
        pal.setColor(QPalette.WindowText, QColor(TEXT))
        pal.setColor(QPalette.Base, QColor(BG2))
        pal.setColor(QPalette.Text, QColor(TEXT))
        self.setPalette(pal)
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background:{BG}; color:{TEXT};
                font-family:Consolas,'Courier New',monospace;
            }}
            QLineEdit {{
                background:rgba(0,20,50,200); border:1px solid {CYAN2};
                border-radius:8px; padding:9px 14px; color:{TEXT}; font-size:13px;
            }}
            QLineEdit:focus {{ border:1px solid {ROG}; }}
            QComboBox {{
                background:rgba(0,20,50,200); border:1px solid {DIM};
                border-radius:6px; padding:4px 10px; color:{TEXT}; font-size:10px;
            }}
            QComboBox::drop-down {{ border:none; }}
            QComboBox QAbstractItemView {{
                background:{BG2}; color:{TEXT}; border:1px solid {DIM};
                selection-background-color:rgba(255,0,51,120);
            }}
        """)

    def _build(self):
        central = QWidget(); self.setCentralWidget(central)
        self._hud = HudBg(central)
        self._hud.setGeometry(0,0,2000,2000)

        root = QVBoxLayout(central)
        root.setContentsMargins(14,10,14,10); root.setSpacing(6)

        # ── Header ────────────────────────────────────────────
        hdr = QHBoxLayout(); hdr.setSpacing(12)
        hdr.addWidget(Logo())

        tcol = QVBoxLayout(); tcol.setSpacing(0)
        t = QLabel("S.T.R.I.X")
        t.setFont(QFont("Consolas",20,QFont.Bold))
        t.setStyleSheet(f"color:{ROG}; letter-spacing:8px; background:transparent;")
        tcol.addWidget(t)
        s = QLabel("STRATEGIC TACTICAL RESPONSE INTELLIGENCE XSYSTEM")
        s.setStyleSheet(f"color:{TDIM}; font-size:8px; letter-spacing:3px; background:transparent;")
        tcol.addWidget(s)
        hdr.addLayout(tcol); hdr.addStretch()

        # Model selector
        mcol = QVBoxLayout(); mcol.setSpacing(2)
        ml = QLabel("ACTIVE MODEL")
        ml.setStyleSheet(f"color:{TDIM}; font-size:8px; letter-spacing:2px; background:transparent;")
        mcol.addWidget(ml)
        self.model_combo = QComboBox()
        self.model_combo.addItem("Loading...")
        self.model_combo.setFixedWidth(180)
        self.model_combo.currentTextChanged.connect(self._on_model_change)
        mcol.addWidget(self.model_combo)
        hdr.addLayout(mcol)

        # TTS toggle
        self.tts_btn = GlitchButton("VOL ON", color="#00ff88")
        self.tts_btn.setFixedWidth(80)
        self.tts_btn.clicked.connect(self._toggle_tts)
        hdr.addWidget(self.tts_btn)

        # Clock + status
        rcol = QVBoxLayout(); rcol.setAlignment(Qt.AlignRight)
        self.clock_lbl = QLabel()
        self.clock_lbl.setStyleSheet(f"color:{CYAN}; font-size:11px; letter-spacing:2px; background:transparent;")
        self.clock_lbl.setAlignment(Qt.AlignRight)
        rcol.addWidget(self.clock_lbl)
        self.status_dot = QLabel("INITIALIZING")
        self.status_dot.setStyleSheet(f"color:#ffaa00; font-size:9px; letter-spacing:3px; background:transparent;")
        self.status_dot.setAlignment(Qt.AlignRight)
        rcol.addWidget(self.status_dot)
        hdr.addLayout(rcol)

        root.addLayout(hdr)
        root.addWidget(GlowLine())
        self.wave = Wave(); root.addWidget(self.wave)

        # ── Content ───────────────────────────────────────────
        content = QHBoxLayout(); content.setSpacing(12)

        # Chat panel
        chat_frame = QFrame()
        chat_frame.setStyleSheet(f"QFrame {{ background:rgba(5,12,30,160); border:1px solid {DIM}; border-radius:10px; }}")
        cfl = QVBoxLayout(chat_frame); cfl.setContentsMargins(0,0,0,0); cfl.setSpacing(0)
        ch_lbl = QLabel("  COMMUNICATION CHANNEL")
        ch_lbl.setStyleSheet(f"color:{TDIM}; font-size:9px; letter-spacing:3px; background:rgba(0,40,80,120); border-bottom:1px solid {DIM}; border-radius:10px 10px 0 0; padding:6px 12px;")
        cfl.addWidget(ch_lbl)
        self.chat_area = ChatArea()
        cfl.addWidget(self.chat_area)
        content.addWidget(chat_frame, stretch=3)

        # Arc Reactor — behind chat, revealed after build
        self._arc = None
        self._arc_frame = chat_frame
        QTimer.singleShot(300, self._mount_arc)

        # ── Right panel ───────────────────────────────────────
        right = QVBoxLayout(); right.setSpacing(8)

        def sec(txt):
            l=QLabel(f"  {txt}")
            l.setStyleSheet(f"color:{ROG}; font-size:9px; letter-spacing:3px; background:transparent;")
            return l

        right.addWidget(sec("SYSTEM METRICS"))
        g1=QHBoxLayout(); g1.setSpacing(6)
        self.cpu_c=StatCard("CPU","cpu"); self.ram_c=StatCard("RAM","ram")
        g1.addWidget(self.cpu_c); g1.addWidget(self.ram_c); right.addLayout(g1)
        g2=QHBoxLayout(); g2.setSpacing(6)
        self.bat_c=StatCard("PWR","power"); self.net_c=StatCard("NET","network")
        g2.addWidget(self.bat_c); g2.addWidget(self.net_c); right.addLayout(g2)

        # ── AI Model panel ────────────────────────────────────
        right.addWidget(sec("AI MODELS"))
        model_frame = QFrame()
        model_frame.setStyleSheet(f"QFrame {{ background:rgba(0,40,80,120); border:1px solid {DIM}; border-radius:6px; }}")
        mfl = QVBoxLayout(model_frame); mfl.setContentsMargins(10,8,10,8); mfl.setSpacing(4)

        for role, model, col in [
            ("CHAT",      "phi3",          "#ff6600"),
            ("REASONING", "llama3.1",      "#aa44ff"),
            ("CODING",    "qwen2.5-coder", "#00cc44"),
        ]:
            row = QHBoxLayout()
            rl = QLabel(role); rl.setStyleSheet(f"color:{TDIM}; font-size:8px; letter-spacing:1px; background:transparent;")
            ml2 = QLabel(model); ml2.setStyleSheet(f"color:{col}; font-size:9px; font-weight:bold; background:transparent;")
            row.addWidget(rl); row.addStretch(); row.addWidget(ml2)
            mfl.addLayout(row)

        right.addWidget(model_frame)

        right.addWidget(sec("ENVIRONMENT"))
        self.weather_lbl = QLabel("Fetching weather...")
        self.weather_lbl.setWordWrap(True)
        self.weather_lbl.setStyleSheet(f"color:{TEXT}; font-size:10px; background:rgba(0,40,80,120); border:1px solid {DIM}; border-left:2px solid {ROG}; border-radius:6px; padding:8px 10px;")
        right.addWidget(self.weather_lbl)

        right.addWidget(sec("QUICK ACCESS"))
        for icon,label,cmd in [
            ("W","Weather",   "what is the weather today"),
            ("N","Tech News", "show me latest technology news"),
            ("S","System",    "show system status"),
            ("C","Crypto",    "show top crypto prices"),
            ("P","Projects",  "list my projects"),
        ]:
            btn=QPushButton(f"  {icon}  {label}")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:rgba(0,50,100,160); color:{CYAN};
                    border:1px solid {DIM}; border-left:2px solid {ROG};
                    border-radius:6px; padding:7px 10px;
                    font-size:11px; text-align:left; letter-spacing:1px;
                }}
                QPushButton:hover {{ background:rgba(255,0,51,60); color:#fff; }}
            """)
            btn.clicked.connect(lambda _,c=cmd: self._send(c))
            right.addWidget(btn)

        exp_btn=QPushButton("  EXPORT CHAT")
        exp_btn.setStyleSheet(f"QPushButton {{ background:rgba(0,30,60,180); color:{TDIM}; border:1px solid {DIM}; border-radius:6px; padding:7px 10px; font-size:10px; text-align:left; }} QPushButton:hover {{ color:{CYAN}; border-color:{CYAN}; }}")
        exp_btn.clicked.connect(self._export_chat)
        right.addWidget(exp_btn)

        right.addStretch()
        content.addLayout(right, stretch=1)
        root.addLayout(content, stretch=1)
        root.addWidget(GlowLine())

        # ── Input row ─────────────────────────────────────────
        inp=QHBoxLayout(); inp.setSpacing(8)
        gt=QLabel(">"); gt.setStyleSheet(f"color:{ROG};font-size:14px;background:transparent;")
        inp.addWidget(gt)

        self.input_field=QLineEdit()
        self.input_field.setPlaceholderText("Type or speak a command...  open/play/ugad/bajao/vaajav + target runs instantly")
        self.input_field.returnPressed.connect(self._on_send)
        self.input_field.textChanged.connect(self._on_text_changed)
        inp.addWidget(self.input_field)

        # ── EXECUTE button ─────────────────────────────────────
        exe_btn = GlitchButton("▶  EXECUTE", color=ROG)
        exe_btn.clicked.connect(self._on_send)
        inp.addWidget(exe_btn)

        # ── STOP button — visible only while running ────────────
        self.stop_btn = GlitchButton("■  STOP", color="#ff0033")
        self.stop_btn.setVisible(False)
        self.stop_btn.setToolTip("Stop everything  [Esc]")
        self.stop_btn.clicked.connect(self._on_stop)
        inp.addWidget(self.stop_btn)

        # ── VOICE button ────────────────────────────────────────
        self.voice_btn = GlitchButton("◉  VOICE", color=CYAN)
        self.voice_btn.clicked.connect(self._on_voice)
        inp.addWidget(self.voice_btn)

        # ── MUTE / UNMUTE button — in input bar ─────────────────
        self.mute_btn = GlitchButton("🔊  VOICE ON", color="#00ff88")
        self.mute_btn.setToolTip("Toggle STRIX voice on/off")
        self.mute_btn.clicked.connect(self._toggle_mute_btn)
        inp.addWidget(self.mute_btn)

        # ── CLEAR button ─────────────────────────────────────────
        clr = GlitchButton("✕", color="#ff4444")
        clr.setFixedWidth(42)
        clr.setToolTip("Clear chat")
        clr.clicked.connect(self._clear)
        inp.addWidget(clr)

        root.addLayout(inp)

        self.status_bar=QLabel("INITIALIZING SYSTEMS...")
        self.status_bar.setStyleSheet(f"color:{TDIM};font-size:9px;letter-spacing:2px;background:transparent;")
        root.addWidget(self.status_bar)

        self._stats_timer=QTimer()
        self._stats_timer.timeout.connect(self._stats)
        self._stats_timer.start(4000)
        QTimer.singleShot(2500, self._stats)

        # Auto-exec timer — fires _on_send after 1.5s pause when action word typed
        self._auto_exec_timer = QTimer()
        self._auto_exec_timer.setSingleShot(True)
        self._auto_exec_timer.timeout.connect(self._on_send)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+L"), self, self._clear)
        QShortcut(QKeySequence("Escape"), self, self._on_stop)

    def _restore_window(self):
        s = QSettings("STRIX", "ROG_AI")
        geo = s.value("geometry")
        if geo: self.restoreGeometry(geo)

    def _mount_arc(self):
        """Place ArcReactor behind the chat area."""
        try:
            frame = self._arc_frame
            self._arc = ArcReactor(frame)
            fw, fh = frame.width(), frame.height()
            # Center the reactor, slightly transparent
            size = min(fw, fh) - 40
            self._arc.setGeometry(
                (fw - size) // 2,
                (fh - size) // 2,
                size, size
            )
            self._arc.setWindowOpacity(0.22)
            self._arc.lower()
            self._arc.show()
        except Exception as ex:
            print(f"[ArcReactor] {ex}")

    def _mount_overlays(self):
        """Add corner brackets and particle field on top of everything."""
        try:
            self._corners = CornerBrackets(self.centralWidget())
            self._corners.setGeometry(0, 0,
                self.centralWidget().width(),
                self.centralWidget().height())
            self._corners.raise_()
            self._corners.show()

            self._particles = ParticleField(self.centralWidget())
            self._particles.setGeometry(0, 0,
                self.centralWidget().width(),
                self.centralWidget().height())
            self._particles.lower()   # particles behind content
            self._particles.show()
        except Exception as e:
            print(f"[Overlays] {e}")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        cw = self.centralWidget()
        if cw:
            if self._corners:
                self._corners.setGeometry(0, 0, cw.width(), cw.height())
            if self._particles:
                self._particles.setGeometry(0, 0, cw.width(), cw.height())

    def closeEvent(self, e):
        # Save window position
        s = QSettings("STRIX", "ROG_AI")
        s.setValue("geometry", self.saveGeometry())

        # Stop stream thread
        if self._stream_thread and self._stream_thread.isRunning():
            self._stream_thread.stop()
            self._stream_thread.quit()
            self._stream_thread.wait(2000)

        # Stop wake word thread
        if self._wake_thread and self._wake_thread.isRunning():
            self._wake_thread.stop_loop()
            self._wake_thread.quit()
            self._wake_thread.wait(2000)

        # Stop TTS threads
        for t in list(self._tts_threads):
            if t.isRunning():
                t.quit()
                t.wait(1000)

        # Stop TTS engine
        if self.tts:
            try:
                self.tts.stop()
            except Exception:
                pass

        super().closeEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._hud.setGeometry(0,0,self.width(),self.height())

    def _tick_clock(self):
        self.clock_lbl.setText(datetime.now().strftime("%d.%m.%Y  %H:%M:%S"))

    def _stats(self):
        try:
            from tools.system_tools import get_cpu_usage,get_ram_usage,get_battery_status,get_network_info
            cpu=get_cpu_usage(); ram=get_ram_usage(); bat=get_battery_status(); net=get_network_info()
            self.cpu_c.set_value(f"{cpu['percent']}%  {cpu['cores']} cores")
            self.ram_c.set_value(f"{ram['used_gb']} / {ram['total_gb']} GB")
            self.bat_c.set_value(f"{bat['percent']}% CHARGING" if bat.get('available') and bat.get('plugged_in') else (f"{bat['percent']}%" if bat.get('available') else "DESKTOP"))
            self.net_c.set_value(net.get('local_ip','N/A'))
        except Exception: pass

    def _lazy_load(self):
        self.input_field.setEnabled(False)
        self.status_bar.setText("LOADING AI CORE...")

        def _load():
            try:
                import sys, os
                # Make sure E:\Strix is in path so brain.core resolves correctly
                strix_root = os.path.dirname(os.path.abspath(__file__))
                if strix_root not in sys.path:
                    sys.path.insert(0, strix_root)
                from brain.core import StrixBrain
                from strix_tts import StrixTTS
                self.brain = StrixBrain()
                self.tts   = StrixTTS()
            except ImportError as e:
                print(f"[STRIX] Import error: {e}")
                print("[STRIX] Make sure E:\\Strix\\brain\\core.py is the latest version")
                # Show error in UI on main thread
                QTimer.singleShot(0, lambda: self.status_bar.setText(f"ERROR: {e}"))
            except Exception as e:
                print(f"[STRIX] Load error: {e}")
                QTimer.singleShot(0, lambda: self.status_bar.setText(f"LOAD ERROR: {e}"))

        threading.Thread(target=_load, daemon=True).start()

        def _check():
            if self.brain is not None:
                self.input_field.setEnabled(True)
                self.status_dot.setText("ONLINE")
                self.status_dot.setStyleSheet(f"color:{GREEN};font-size:9px;letter-spacing:3px;background:transparent;")
                mt = ModelListThread(); mt.ready.connect(self._populate_models); mt.start(); self._mt = mt
                self._pre = PreloadThread()
                self._pre.weather_ready.connect(lambda t: self.weather_lbl.setText(clean_text(t)))
                self._pre.start()
                self._start_wake_listener()
                self._run_boot_sequence()
            else:
                QTimer.singleShot(200, _check)

        QTimer.singleShot(200, _check)

    def _populate_models(self, models):
        self.model_combo.clear()
        if models:
            for m in models: self.model_combo.addItem(m)
        else:
            self.model_combo.addItem("No models found")

    def _on_model_change(self, model):
        if not model or "Loading" in model or "No models" in model: return
        try:
            from models.llm_interface import set_models
            set_models(reasoning=model, coding=model)
            self.status_bar.setText(f"Model override: {model}")
        except Exception: pass

    def _start_wake_listener(self):
        self._wake_thread = WakeWordThread()
        self._wake_thread.wake.connect(self._on_wake)
        self._wake_thread.command.connect(self._on_wake_command)
        self._wake_thread.start()
        # Watchdog — unstick the wake thread every 8s if input is free
        self._wake_watchdog = QTimer(self)
        self._wake_watchdog.timeout.connect(self._wake_watchdog_tick)
        self._wake_watchdog.start(8000)

    def _wake_watchdog_tick(self):
        """Periodically force-unstick wake thread if UI is idle."""
        if self._wake_thread and self.input_field.isEnabled():
            if self._wake_thread._paused or self._wake_thread._hard_muted:
                self._wake_thread._paused     = False
                self._wake_thread._hard_muted = False
                print("[Wake] Watchdog unstuck wake thread")

    def _run_boot_sequence(self):
        """Show boot lines one by one, then speak the greeting."""
        self._boot_lines = list(BOOT_SEQUENCE)
        self._boot_index = 0
        self._boot_timer = QTimer(self)
        self._boot_timer.timeout.connect(self._boot_next_line)
        self._boot_timer.start(600)   # one line every 600ms

    def _boot_next_line(self):
        if self._boot_index < len(self._boot_lines):
            line = self._boot_lines[self._boot_index]
            self.status_bar.setText(line)
            self._boot_index += 1
        else:
            self._boot_timer.stop()
            self.status_bar.setText("ALL SYSTEMS OPERATIONAL — phi3 | llama3.1 | qwen2.5-coder")
            # Now show greeting bubble and speak it
            greeting = get_startup_message()
            self.chat_area.add_message("STRIX", greeting, True, "phi3:latest")
            self._speak(greeting)

    @Slot()
    def _on_wake(self):
        # Restore window if minimized or hidden
        if self.isMinimized() or not self.isVisible():
            self.showNormal()
            self.raise_()
            self.activateWindow()
            QTimer.singleShot(300, self._on_wake_respond)
        else:
            self._on_wake_respond()

    def _on_wake_respond(self):
        if not self.input_field.isEnabled(): return
        self.raise_()
        self.activateWindow()
        self.input_field.setFocus()
        self.chat_area.add_message("STRIX","Yes Boss, I am listening.",True,"phi3:latest")
        self._speak("Yes Boss")
        QTimer.singleShot(400, self._on_voice)

    def _on_wake_command(self, text: str):
        """Direct voice command — always executes, no button press needed."""
        if not text or not text.strip():
            return
        # Restore window if hidden
        if self.isMinimized() or not self.isVisible():
            self.showNormal(); self.raise_(); self.activateWindow()
        # Always force field enabled so command can run immediately
        self.input_field.setEnabled(True)
        self.input_field.setText(text.strip())
        self._on_send()

    def _tts_style(self, muted):
        # Legacy — kept for compat but GlitchButton handles its own style
        col = "#ff4444" if muted else "#00ff88"
        bg  = "rgba(40,10,10,200)" if muted else "rgba(0,30,60,200)"
        return f"QPushButton {{ background:{bg}; color:{col}; border:1px solid {col}; border-radius:8px; padding:5px 8px; font-size:9px; letter-spacing:1px; }}"

    def _toggle_tts(self):
        muted = self.tts.toggle_mute() if self.tts else False
        self.tts_btn.setText("VOL OFF" if muted else "VOL ON")
        self.tts_btn.setStyleSheet(self._tts_style(muted))

    def _toggle_mute_btn(self):
        """Input-bar mute button — synced with header VOL toggle."""
        muted = self.tts.toggle_mute() if self.tts else False
        if muted:
            self.mute_btn.setText("🔇  MUTED")
            self.mute_btn._base_color = "#ff4444"
            self.mute_btn.set_active(False, "#ff4444")
            self.tts_btn.setText("VOL OFF")
        else:
            self.mute_btn.setText("🔊  VOICE ON")
            self.mute_btn._base_color = "#00ff88"
            self.mute_btn.set_active(True, "#00ff88")
            self.tts_btn.setText("VOL ON")
        self.tts_btn.setStyleSheet(self._tts_style(muted))

    def _speak(self, text):
        if not self.tts or not self.tts.available:
            return
        if self._arc:
            self._arc.set_speaking(True)
        # Hard-mute mic while speaking — stops STRIX hearing itself
        if self._wake_thread:
            self._wake_thread.hard_mute()
        t = TTSThread(self.tts, text)
        t.finished.connect(self._on_tts_done)
        t.finished.connect(lambda: self._tts_threads.remove(t) if t in self._tts_threads else None)
        self._tts_threads.append(t)
        t.start()

    def _on_tts_done(self):
        alive = [t for t in self._tts_threads if t.isRunning()]
        if not alive:
            if self._arc:
                self._arc.set_speaking(False)
            # 1.5s delay — lets TTS audio fully decay before mic reopens
            QTimer.singleShot(1500, self._resume_wake)

    def _resume_wake(self):
        """Unmute mic after TTS audio has fully decayed."""
        if self._wake_thread:
            self._wake_thread.hard_unmute()
            self._wake_thread.resume()
            # Safety — force _paused=False in case it got stuck
            self._wake_thread._paused = False

    def _send(self, text):
        self.input_field.setText(text); self._on_send()

    # Keywords that execute immediately when typed or spoken — no Enter needed
    # English + Hindi + Marathi command prefixes
    AUTO_EXEC_PREFIXES = (
        # ── English ───────────────────────────────────────────
        "open ", "play ", "launch ", "start ", "run ",
        "close ", "kill ", "search for ", "find ",
        "create ", "make ", "go to ", "visit ",
        "write code", "write a ", "write me ",
        "create a python", "create a javascript", "create a html",
        "create a file", "create a script",
        "locate ", "where is ", "find this ", "find my ",
        "work time", "work mode", "coding time", "dev mode",
        "show anime", "watch anime", "open anime",
        "shutdown", "shut down", "bye strix", "goodnight",
        "show ", "display ", "get ",
        "pause", "stop music", "next track", "previous track",
        # ── Hindi ─────────────────────────────────────────────
        "kholo ", "bajao ", "band karo", "chalu karo",
        "dikhao ", "batao ", "rok ", "ruk ",
        "agla ", "pichla ", "gaana bajao",
        # ── Marathi ───────────────────────────────────────────
        "ugad ", "ugaad ", "ughad ",
        "vaajav ", "gana lav", "gaana lav",
        "thambav", "band kar",
        "daakhav ", "sang ", "saang ",
        "shod ", "shodh ", "banav ",
        "kaam chalu", "kaam suru",
    )

    def _on_text_changed(self, text: str):
        """Auto-submit typed action commands — no Enter needed."""
        tl = text.lower().strip()

        # Instant exec — complete short commands (e.g. "open chrome", "play spotify")
        # If text starts with action prefix AND has a clear target word, fire immediately
        INSTANT_TARGETS = {
            "chrome", "youtube", "spotify", "github", "gmail", "discord",
            "notepad", "calculator", "vscode", "cmd", "powershell",
            "whatsapp", "telegram", "netflix", "reddit", "chatgpt", "gemini",
            "anime", "work mode", "work time", "coding time",
        }
        for prefix in self.AUTO_EXEC_PREFIXES:
            if tl.startswith(prefix):
                after = tl[len(prefix):].strip()
                # If the target is a known app/site — fire instantly (0ms)
                if any(t in after for t in INSTANT_TARGETS):
                    self._auto_exec_timer.stop()
                    self._auto_exec_timer.start(0)
                    return
                # Otherwise wait 0.8s after user stops typing
                if len(after) > 2:
                    self._auto_exec_timer.start(800)
                    return
        self._auto_exec_timer.stop()

    def _on_send(self):
        text = self.input_field.text().strip()
        if not text or not self.brain: return
        self._auto_exec_timer.stop()
        self.input_field.clear()

        # Stop any ongoing TTS immediately when new command arrives
        if self.tts:
            self.tts.stop()

        # ── Music state — set flag BEFORE processing (immediate) ──
        tl = text.lower()
        if self._wake_thread:
            # Starting music? Raise guard NOW
            if any(w in tl for w in [
                "play ", "playlist", "put on", "song", "music on",
                "play my ", "play some",
            ]):
                self._wake_thread.music_started()
            # Stopping/pausing? Drop guard NOW
            elif any(w in tl for w in [
                "pause", "stop music", "stop song", "stop playing",
                "pause music", "pause song", "music off", "stop it",
                "stop that", "shut up",
            ]):
                self._wake_thread.music_stopped()

        # Stop any ongoing stream
        if self._stream_thread and self._stream_thread.isRunning():
            self._stream_thread.stop()

        self.chat_area.add_message("YOU", text, False)
        self.wave.set_active(True)
        self.status_bar.setText("PROCESSING...")
        self.status_dot.setText("THINKING")
        self.status_dot.setStyleSheet(f"color:{GOLD};font-size:9px;letter-spacing:3px;background:transparent;")
        self.input_field.setEnabled(False)
        self.stop_btn.setVisible(True)
        self.stop_btn.trigger_glitch()
        # Only pause wake listener for real LLM chat queries
        # Action commands (open/play/find/etc.) are instant — no need to pause
        tl_check = text.lower()
        _is_action = any(tl_check.startswith(p)
                         for p in WakeWordThread.ACTION_PREFIXES)
        if not _is_action and self._wake_thread:
            self._wake_thread.pause()

        # Show typing indicator with detected model
        detected = self._detect_model_for_display(text)
        self.chat_area.show_typing(detected)
        self._current_model = detected

        self._streaming_bubble = None
        self._stream_thread = StreamThread(self.brain, text)
        self._stream_thread.token.connect(self._on_token)
        self._stream_thread.done.connect(self._on_done)
        self._stream_thread.start()

    def _detect_model_for_display(self, text: str) -> str:
        """Predict which model will handle this — for the typing indicator."""
        tl = text.lower()
        code_langs = ["python","java","javascript","html","css","c++","typescript","sql"]
        code_acts  = ["write","create","make","build","generate","code","function","script","debug","fix"]
        if any(l in tl for l in code_langs) and any(a in tl for a in code_acts):
            return "qwen2.5-coder"
        reason_words = ["why","explain","how does","difference","compare","analyse","plan","suggest"]
        if any(w in tl for w in reason_words):
            return "llama3.1"
        return "phi3:latest"

    @Slot(str)
    def _on_token(self, token):
        if self._streaming_bubble is None:
            self._streaming_bubble = self.chat_area.add_streaming_bubble(self._current_model)
        self._streaming_bubble.append(token)
        self.chat_area._scroll_bottom()

    @Slot(str)
    def _on_done(self, full_text):
        # ── Shutdown signal ───────────────────────────────────
        # ── KILL — silent wipe + immediate close ─────────────
        if full_text.strip() == "STRIX_KILL":
            self.chat_area.hide_typing()
            self.status_bar.setText("...")
            # Wipe all chat bubbles from the UI
            try:
                layout = self.chat_area._scroll_widget.layout()
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
            except Exception:
                pass
            # Wipe memory DB
            try:
                from memory.memory_db import clear_chat_history
                clear_chat_history()
            except Exception:
                pass
            # Stop TTS + threads silently
            try: self._tts.stop()
            except Exception: pass
            try:
                if self._stream_thread: self._stream_thread.stop()
            except Exception: pass
            QTimer.singleShot(300, self.close)
            return

        # ── SHUTDOWN — graceful goodbye ───────────────────────
        if full_text.strip() == "STRIX_SHUTDOWN":
            goodbye = random.choice([
                "Goodbye Boss. STRIX going offline.",
                "Shutting down. See you next time, Boss.",
                "STRIX signing off. Come back when you need me, Boss.",
                "Powering down. It was an honor, Boss.",
            ])
            self.chat_area.hide_typing()
            self.chat_area.add_message("STRIX", goodbye, True, "phi3:latest")
            self.status_bar.setText("SHUTTING DOWN...")
            self._speak(goodbye)
            QTimer.singleShot(3500, self.close)
            return

        if self._streaming_bubble:
            self.chat_area.replace_streaming_bubble(self._streaming_bubble, full_text)
            self._streaming_bubble = None
        else:
            # Tool result — no streaming, just add bubble
            self.chat_area.hide_typing()
            self.chat_area.add_message("STRIX", full_text, True, "tool")

        self.wave.set_active(False)
        self.stop_btn.setVisible(False)
        self.status_bar.setText("READY")
        self.status_dot.setText("ONLINE")
        self.status_dot.setStyleSheet(f"color:{GREEN};font-size:9px;letter-spacing:3px;background:transparent;")
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        # Resume soft-pause (LLM query finished)
        # Do NOT clear hard_muted here — that belongs to _resume_wake after TTS
        if self._wake_thread:
            self._wake_thread._paused = False

        # ── Music state — confirm via response (backup) ───────
        ft_lower = full_text.lower()
        if self._wake_thread:
            if any(x in ft_lower for x in [
                "now playing", "playing your playlist", "queued",
                "playing boss", "opening spotify",
            ]):
                self._wake_thread.music_started()
            elif any(x in ft_lower for x in [
                "paused", "music paused", "spotify stopped", "music stopped",
            ]):
                self._wake_thread.music_stopped()

        self._speak(full_text)

    def _on_stop(self):
        """Stop EVERYTHING — stream, TTS, voice listener."""
        # 1. Stop TTS immediately
        try: self._tts.stop()
        except Exception: pass
        # 2. Stop streaming thread
        try:
            if self._stream_thread: self._stream_thread.stop()
        except Exception: pass
        # 3. Stop arc reactor speaking state
        try: self.arc.set_speaking(False)
        except Exception: pass
        # 4. Clean up UI
        self.stop_btn.setVisible(False)
        self.wave.set_active(False)
        self.status_bar.setText("READY")
        self.status_dot.setText("ONLINE")
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        if self._streaming_bubble:
            partial = self._streaming_bubble.full_text()
            try: self.chat_area.replace_streaming_bubble(self._streaming_bubble, partial or "— Stopped —")
            except Exception: pass
            self._streaming_bubble = None
        if self._wake_thread: self._wake_thread.resume()

    def _on_voice(self):
        self.voice_btn.setText("◉  LISTENING")
        self.voice_btn.setEnabled(False)
        self.voice_btn.trigger_glitch()
        self.wave.set_active(True)
        self.status_bar.setText("LISTENING... SPEAK NOW")
        if self._wake_thread: self._wake_thread.pause()

        def _listen():
            try:
                from brain.input_processor import VoiceInput
                vi=VoiceInput(); text=vi.listen_once(timeout=8,phrase_limit=20)
            except Exception: text=""
            self._voice_result = text
            from PySide6.QtCore import QMetaObject
            QMetaObject.invokeMethod(self,"_on_voice_done",Qt.QueuedConnection)

        threading.Thread(target=_listen, daemon=True).start()

    @Slot()
    def _on_voice_done(self):
        text = getattr(self, "_voice_result", "")
        self.voice_btn.setText("◉  VOICE")
        self.voice_btn.setEnabled(True)
        self.wave.set_active(False)
        if self._wake_thread:
            self._wake_thread.resume()
        if text:
            self.input_field.setText(text)
            # Direct command words — execute immediately, no extra wait
            tl = text.lower().strip()
            is_direct = any(tl.startswith(p) for p in self.AUTO_EXEC_PREFIXES)
            if is_direct:
                print(f"[Voice] Direct command detected: '{text}' — executing now")
                self._on_send()
            else:
                # Regular query — still auto-submit but show text first
                self._on_send()
        else:
            self.status_bar.setText("VOICE: NOTHING HEARD — TRY AGAIN")

    def _clear(self):
        layout = self.chat_area._layout
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        if self.brain: self.brain.clear_memory()
        self.chat_area.add_message("STRIX","Memory cleared. New session ready Boss.",True,"phi3:latest")

    def _export_chat(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Chat",
            f"strix_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt)")
        if not path: return
        try:
            history = self.brain.get_history(limit=200) if self.brain else []
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"STRIX Chat Export — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*60+"\n\n")
                for msg in history:
                    role = "STRIX" if msg["role"]=="assistant" else "YOU"
                    f.write(f"[{role}]\n{msg['content']}\n\n")
            self.status_bar.setText(f"Exported: {path}")
        except Exception as e:
            self.status_bar.setText(f"Export failed: {e}")


# ── Entry ─────────────────────────────────────────────────────
def run_gui():
    app = QApplication(sys.argv)
    app.setApplicationName("STRIX")
    pal = QPalette()
    pal.setColor(QPalette.Window,    QColor(BG))
    pal.setColor(QPalette.WindowText,QColor(TEXT))
    pal.setColor(QPalette.Base,      QColor(BG2))
    pal.setColor(QPalette.Text,      QColor(TEXT))
    app.setPalette(pal)

    # ── Show splash, then open main window ──────────────
    splash = StrixSplash()
    splash.show()

    _main_win = []

    def _on_splash_done():
        w = StrixWindow()
        _main_win.append(w)

        # Animate main window in — fade from 0 to 1
        w.setWindowOpacity(0.0)
        w.show()

        fade_in = QPropertyAnimation(w, b"windowOpacity")
        fade_in.setDuration(600)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.InOutCubic)
        fade_in.start()
        # Keep reference so it doesn't get GC'd
        w._fade_anim = fade_in

    splash.finished.connect(_on_splash_done)

    sys.exit(app.exec())

if __name__=="__main__":
    run_gui()