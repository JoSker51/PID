

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.widgets import Slider, Button
from matplotlib.animation import FuncAnimation

# ── Parámetros del modelo físico del horno ─────────────────────────────────
TAU     = 20.0   # constante de tiempo [s] — qué tan lento calienta/enfría
K_PLANT = 3.5    # ganancia de la planta  — °C por % de potencia
DT      = 0.5    # paso de tiempo de integración [s]
T0      = 0.0    # temperatura inicial [°C]
SP0     = 150.0  # setpoint inicial [°C]
MAX_T   = 250    # segundos a mostrar en la ventana deslizante

# ── Parámetros PID iniciales ────────────────────────────────────────────────
KP0 = 2.0
KI0 = 0.05
KD0 = 1.0

# ── Estado de la simulación ─────────────────────────────────────────────────
class SimState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.T        = T0       # temperatura actual
        self.integral = 0.0      # acumulador integral
        self.prev_err = SP0 - T0 # error anterior para derivada
        self.t        = 0.0      # tiempo simulado

        # Historial para graficar
        self.hist_t   = [0.0]
        self.hist_T   = [T0]
        self.hist_u   = [0.0]
        self.hist_sp  = [SP0]
        self.hist_P   = [0.0]
        self.hist_I   = [0.0]
        self.hist_D   = [0.0]

        # Registro de perturbaciones para anotaciones
        self.perturbations = []  # lista de tiempos donde ocurrió una perturbación

sim = SimState()

# ── Layout de la figura ──────────────────────────────────────────────────────
fig = plt.figure(figsize=(14, 9), facecolor='#f8f8f6')
fig.canvas.manager.set_window_title("Simulador PID — Horno de temperatura")

gs = gridspec.GridSpec(
    3, 2,
    left=0.08, right=0.97,
    top=0.93,  bottom=0.33,
    hspace=0.45, wspace=0.35
)

ax_temp  = fig.add_subplot(gs[0:2, 0])   # temperatura (grande)
ax_u     = fig.add_subplot(gs[2,   0])   # señal de control u(t)
ax_pid   = fig.add_subplot(gs[0:2, 1])   # componentes P, I, D
ax_phase = fig.add_subplot(gs[2,   1])   # plano de fase: error vs dError

for ax in [ax_temp, ax_u, ax_pid, ax_phase]:
    ax.set_facecolor('#ffffff')
    ax.tick_params(labelsize=8)

# ── Líneas iniciales ────────────────────────────────────────────────────────
ln_T,     = ax_temp.plot([], [], color='#185FA5', lw=2,   label='Temperatura T(t)')
ln_sp,    = ax_temp.plot([], [], color='#1D9E75', lw=1.5, ls='--', label='Setpoint')
ax_temp.set_ylabel('Temperatura (°C)', fontsize=9)
ax_temp.set_title('Respuesta del horno', fontsize=10, fontweight='normal')
ax_temp.legend(fontsize=8, loc='lower right')
ax_temp.set_ylim(-30, 350)
ax_temp.set_xlim(0, MAX_T)
ax_temp.grid(True, alpha=0.25)

ln_u,     = ax_u.plot([], [], color='#D85A30', lw=1.5,  label='u(t) — potencia %')
ax_u.set_ylabel('Potencia (%)', fontsize=9)
ax_u.set_xlabel('Tiempo (s)',   fontsize=9)
ax_u.set_ylim(-5, 110)
ax_u.set_xlim(0, MAX_T)
ax_u.axhline(100, color='#D85A30', lw=0.8, ls=':', alpha=0.5)
ax_u.axhline(0,   color='#888',    lw=0.8, ls=':', alpha=0.3)
ax_u.legend(fontsize=8, loc='upper right')
ax_u.grid(True, alpha=0.25)

ln_P,     = ax_pid.plot([], [], color='#185FA5', lw=1.5, label='P = Kp·e')
ln_I,     = ax_pid.plot([], [], color='#1D9E75', lw=1.5, label='I = Ki·∫e')
ln_D,     = ax_pid.plot([], [], color='#D85A30', lw=1.5, label='D = Kd·de/dt')
ax_pid.set_ylabel('Contribución (u)', fontsize=9)
ax_pid.set_title('Componentes P / I / D', fontsize=10, fontweight='normal')
ax_pid.legend(fontsize=8, loc='upper right')
ax_pid.set_ylim(-150, 350)
ax_pid.set_xlim(0, MAX_T)
ax_pid.axhline(0, color='#888', lw=0.8, alpha=0.3)
ax_pid.grid(True, alpha=0.25)

ln_phase, = ax_phase.plot([], [], color='#7F77DD', lw=1.2, alpha=0.8)
dot_phase,= ax_phase.plot([], [], 'o', color='#7F77DD', ms=6)
ax_phase.set_xlabel('Error e(t) (°C)',     fontsize=9)
ax_phase.set_ylabel('d(error)/dt (°C/s)',  fontsize=9)
ax_phase.set_title('Plano de fase',        fontsize=10, fontweight='normal')
ax_phase.axhline(0, color='#888', lw=0.8, alpha=0.3)
ax_phase.axvline(0, color='#888', lw=0.8, alpha=0.3)
ax_phase.grid(True, alpha=0.25)

# Métricas en texto
txt_T  = fig.text(0.12, 0.945, 'T = 0.0 °C',      fontsize=10, color='#185FA5', fontweight='bold')
txt_e  = fig.text(0.30, 0.945, 'Error = 150.0 °C', fontsize=10, color='#D85A30')
txt_u  = fig.text(0.48, 0.945, 'u(t) = 0 %',       fontsize=10, color='#D85A30')
txt_t  = fig.text(0.66, 0.945, 't = 0 s',           fontsize=10, color='#888888')
txt_st = fig.text(0.81, 0.945, '',                   fontsize=10, color='#1D9E75', fontweight='bold')

# ── Sliders ──────────────────────────────────────────────────────────────────
sl_color = '#e8e8e4'

ax_kp = fig.add_axes([0.10, 0.24, 0.35, 0.025], facecolor=sl_color)
ax_ki = fig.add_axes([0.10, 0.19, 0.35, 0.025], facecolor=sl_color)
ax_kd = fig.add_axes([0.10, 0.14, 0.35, 0.025], facecolor=sl_color)
ax_sp = fig.add_axes([0.10, 0.09, 0.35, 0.025], facecolor=sl_color)

sl_kp = Slider(ax_kp, 'Kp (proporcional)', 0.0, 10.0, valinit=KP0, valstep=0.1, color='#185FA5')
sl_ki = Slider(ax_ki, 'Ki (integral)',      0.0,  0.5, valinit=KI0, valstep=0.01, color='#1D9E75')
sl_kd = Slider(ax_kd, 'Kd (derivativo)',    0.0, 10.0, valinit=KD0, valstep=0.1, color='#D85A30')
sl_sp = Slider(ax_sp, 'Setpoint (°C)',     50.0, 300.0,valinit=SP0, valstep=5.0, color='#888888')

for sl in [sl_kp, sl_ki, sl_kd, sl_sp]:
    sl.label.set_fontsize(9)
    sl.valtext.set_fontsize(9)

# ── Botones ──────────────────────────────────────────────────────────────────
ax_btn_perturb = fig.add_axes([0.58, 0.18, 0.18, 0.055])
ax_btn_reset   = fig.add_axes([0.58, 0.10, 0.18, 0.055])
ax_btn_pause   = fig.add_axes([0.78, 0.18, 0.18, 0.055])

btn_perturb = Button(ax_btn_perturb, 'Perturbación\n(abrir puerta −30°C)',
                     color='#FAECE7', hovercolor='#F5C4B3')
btn_reset   = Button(ax_btn_reset,   'Reiniciar simulación',
                     color='#E1F5EE', hovercolor='#9FE1CB')
btn_pause   = Button(ax_btn_pause,   'Pausar / Reanudar',
                     color='#f0f0ec', hovercolor='#ddddd8')

for btn in [btn_perturb, btn_reset, btn_pause]:
    btn.label.set_fontsize(8.5)

# Nota explicativa sobre perturbaciones
fig.text(0.58, 0.275,
         "Perturbación: simula la apertura brusca\n"
         "de la puerta del horno. El PID detecta\n"
         "el error y recupera el setpoint solo.",
         fontsize=8, color='#666666',
         verticalalignment='top',
         bbox=dict(boxstyle='round,pad=0.4', facecolor='#fafaf8', edgecolor='#cccccc', lw=0.8))

# ── Lógica de simulación ────────────────────────────────────────────────────
paused = [False]
perturb_annotations = []

def pid_step():
    """Un paso de integración Euler del sistema horno + PID."""
    kp = sl_kp.val
    ki = sl_ki.val
    kd = sl_kd.val
    sp = sl_sp.val

    err       = sp - sim.T
    sim.integral += err * DT
    d_err     = (err - sim.prev_err) / DT
    sim.prev_err = err

    term_P = kp * err
    term_I = ki * sim.integral
    term_D = kd * d_err

    u = np.clip(term_P + term_I + term_D, 0, 100)

    # Ecuación diferencial del horno: τ·dT/dt = -T + K·u
    dT = ((-sim.T + K_PLANT * u) / TAU) * DT
    sim.T  += dT
    sim.t  += DT

    # Guardar historial
    sim.hist_t.append(sim.t)
    sim.hist_T.append(sim.T)
    sim.hist_u.append(u)
    sim.hist_sp.append(sp)
    sim.hist_P.append(term_P)
    sim.hist_I.append(term_I)
    sim.hist_D.append(term_D)

    return err, d_err, u

def get_window(data):
    """Retorna la ventana de tiempo deslizante para graficar."""
    t_arr = np.array(sim.hist_t)
    t_max = sim.t
    t_min = max(0, t_max - MAX_T)
    mask  = t_arr >= t_min
    return t_arr[mask], mask

def update(frame):
    if paused[0]:
        return

    # Avanzar 3 pasos por frame para velocidad razonable
    for _ in range(3):
        err, d_err, u = pid_step()

    t_arr, mask = get_window(sim.hist_t)
    T_arr  = np.array(sim.hist_T)[mask]
    u_arr  = np.array(sim.hist_u)[mask]
    sp_arr = np.array(sim.hist_sp)[mask]
    P_arr  = np.array(sim.hist_P)[mask]
    I_arr  = np.array(sim.hist_I)[mask]
    D_arr  = np.array(sim.hist_D)[mask]

    t_min = t_arr[0] if len(t_arr) else 0
    t_max = t_arr[-1] if len(t_arr) else MAX_T
    x_max = max(t_max, MAX_T)
    x_min = x_max - MAX_T

    # Actualizar gráficas
    ln_T.set_data(t_arr, T_arr)
    ln_sp.set_data(t_arr, sp_arr)
    ax_temp.set_xlim(x_min, x_max)

    ln_u.set_data(t_arr, u_arr)
    ax_u.set_xlim(x_min, x_max)

    ln_P.set_data(t_arr, P_arr)
    ln_I.set_data(t_arr, I_arr)
    ln_D.set_data(t_arr, D_arr)
    ax_pid.set_xlim(x_min, x_max)

    # Plano de fase (últimos 150 puntos)
    errs = np.array(sim.hist_sp) - np.array(sim.hist_T)
    d_errs = np.gradient(errs, DT)
    n = min(150, len(errs))
    ln_phase.set_data(errs[-n:], d_errs[-n:])
    dot_phase.set_data([errs[-1]], [d_errs[-1]])
    ax_phase.relim(); ax_phase.autoscale_view()

    # Métricas en texto
    txt_T.set_text(f'T = {sim.T:.1f} °C')
    txt_e.set_text(f'Error = {err:.1f} °C')
    txt_u.set_text(f'u(t) = {u:.0f} %')
    txt_t.set_text(f't = {sim.t:.0f} s')

    # Estado del sistema
    if abs(err) < 2:
        txt_st.set_text('✓ Estable')
        txt_st.set_color('#1D9E75')
    elif abs(err) > 30:
        txt_st.set_text('⚠ Recuperando...')
        txt_st.set_color('#D85A30')
    else:
        txt_st.set_text('~ Convergiendo')
        txt_st.set_color('#BA7517')

    # Anotar perturbaciones en la gráfica de temperatura
    for ann in perturb_annotations:
        ann.remove()
    perturb_annotations.clear()
    for pt in sim.perturbations:
        if x_min <= pt <= x_max:
            ann = ax_temp.axvline(pt, color='#D85A30', lw=1, ls=':', alpha=0.7)
            txt = ax_temp.text(pt + 0.5, 15, 'perturbación', fontsize=7,
                               color='#D85A30', rotation=90, va='bottom', alpha=0.8)
            perturb_annotations.extend([ann, txt])

# ── Callbacks de botones ────────────────────────────────────────────────────
def on_perturb(event):
    """Simula apertura de puerta: baja temperatura 30°C bruscamente."""
    sim.T = max(sim.T - 30, -20)
    # Anular la integral acumulada parcialmente para que no haya windup
    sim.integral *= 0.5
    sim.perturbations.append(sim.t)
    print(f"[t={sim.t:.0f}s] Perturbación aplicada → T bajó a {sim.T:.1f}°C")

def on_reset(event):
    """Reinicia toda la simulación al estado inicial."""
    sim.reset()
    for ann in perturb_annotations:
        try: ann.remove()
        except: pass
    perturb_annotations.clear()
    print("Simulación reiniciada.")

def on_pause(event):
    paused[0] = not paused[0]
    state = "Pausada" if paused[0] else "Reanudada"
    print(f"Simulación {state}.")

btn_perturb.on_clicked(on_perturb)
btn_reset.on_clicked(on_reset)
btn_pause.on_clicked(on_pause)

# ── Animación ────────────────────────────────────────────────────────────────
ani = FuncAnimation(fig, update, interval=100, cache_frame_data=False)

plt.suptitle('Controlador PID — Simulación de horno de temperatura',
             fontsize=11, fontweight='normal', color='#333333', y=0.98)

print("=" * 55)
print("  Simulador PID — Horno de temperatura")
print("=" * 55)
print("  Controles:")
print("  · Sliders Kp, Ki, Kd: ajustan las ganancias en vivo")
print("  · Slider Setpoint: cambia la temperatura objetivo")
print("  · Botón 'Perturbación': baja T bruscamente -30°C")
print("  · Botón 'Reiniciar': vuelve al estado inicial")
print("  · Botón 'Pausar': congela la simulación")
plt.show()
