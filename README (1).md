# Simulador de Controlador PID — Horno de Temperatura

**Sistemas Complejos · Cibernética**  
Programa de Ciencias de la Computación e Inteligencia Artificial  
Universidad Sergio Arboleda · Bogotá

---

## Descripción general

Este proyecto implementa una simulación interactiva de un **controlador PID** (Proporcional-Integral-Derivativo) aplicado al control de temperatura de un horno. La simulación permite explorar en tiempo real cómo cada componente del controlador contribuye a llevar el sistema desde una temperatura inicial de 0 °C hasta un setpoint objetivo de 150 °C, y cómo el sistema se recupera de perturbaciones externas sin intervención manual.

El ejercicio se enmarca en los principios de la **cibernética**, disciplina que estudia los mecanismos de control y retroalimentación en sistemas, tanto biológicos como artificiales. En términos de las diapositivas del curso, este simulador ejemplifica directamente el mecanismo de **retroalimentación (feedback)** y la **Ley de la Variedad Requerida de Ashby**: el controlador debe tener tanta variedad de acciones (las tres ganancias Kp, Ki, Kd actuando sobre distintas propiedades del error) como variedad de perturbaciones puede enfrentar el sistema.

---

## Instalación y ejecución

**Requisitos:** Python 3.8 o superior.

```bash
# Instalar dependencias
pip install matplotlib numpy

# Ejecutar la simulación
python pid_horno.py
```

---

## Modelo matemático

### La planta: el horno

El horno se modela como un **sistema dinámico de primer orden**, que es la representación estándar para sistemas con inercia térmica (calefactores, motores, tanques). Su ecuación diferencial es:

```
τ · dT/dt = -T + K · u(t)
```

| Símbolo | Valor usado | Significado |
|---------|-------------|-------------|
| `T`     | variable    | Temperatura actual del horno (°C) |
| `u(t)`  | 0 – 100 %   | Potencia del calefactor (señal de control) |
| `τ`     | 20 s        | Constante de tiempo: inercia térmica del horno |
| `K`     | 1.8         | Ganancia de la planta (°C por unidad de potencia) |

La constante `τ = 20 s` determina qué tan lento responde el horno. Físicamente, si se aplicara potencia máxima constante y no hubiera controlador, el horno tardaría aproximadamente `5τ = 100 s` en alcanzar su temperatura de equilibrio. El término `-T` representa las pérdidas de calor al ambiente.

La ecuación se integra numéricamente mediante el **método de Euler** con paso `DT = 0.5 s`:

```
T(t + DT) = T(t) + DT · [(-T(t) + K · u(t)) / τ]
```

### El controlador PID

El controlador calcula la potencia `u(t)` en cada instante a partir del **error** `e(t) = setpoint - T(t)`:

```
u(t) = Kp · e(t)  +  Ki · ∫e(t)dt  +  Kd · de(t)/dt
```

Cada término tiene un rol distinto y bien definido:

**Término proporcional `P = Kp · e(t)`**  
Reacciona al error *actual*. Si la temperatura está lejos del setpoint, aplica más potencia. Si está cerca, reduce la potencia. Es la acción más inmediata del controlador, pero por sí sola no puede eliminar completamente el error en estado estacionario: siempre queda un residuo llamado *offset*, porque cuando el error tiende a cero, la potencia también tiende a cero, y el horno se enfría ligeramente por debajo del setpoint.

**Término integral `I = Ki · ∫e(t)dt`**  
Acumula el error a lo largo del tiempo. Si el sistema tiene un offset persistente, aunque sea pequeño, la integral lo va sumando y eventualmente genera suficiente potencia adicional para eliminarlo. Es la memoria del controlador: recuerda cuánto error ha acumulado desde el inicio. Su contrapartida es el fenómeno de *windup integral*: si el sistema tarda mucho en responder (por ejemplo, justo después de una perturbación grande), la integral puede acumularse en exceso y causar sobrepaso (*overshoot*).

**Término derivativo `D = Kd · de(t)/dt`**  
Reacciona a la *velocidad de cambio* del error. Si la temperatura está subiendo muy rápido hacia el setpoint, el término D anticipa que podría pasarse y aplica un freno reduciendo la potencia antes de llegar. Funciona como un amortiguador: no mira dónde está el error, sino con qué velocidad está cambiando. Reduce el overshoot y mejora la estabilidad, pero es sensible al ruido en la medición.

La señal de control se limita al rango físico del calefactor:

```python
u = clip(P + I + D, 0, 100)
```

---

## Descripción de las gráficas

El simulador muestra cuatro gráficas simultáneas. A continuación se explica qué representa cada una y cómo interpretarla.

### 1. Respuesta del horno — T(t) vs tiempo

Esta es la gráfica principal. Muestra dos curvas:

- **Línea azul sólida `T(t)`:** la temperatura real del horno en cada instante.
- **Línea verde punteada:** el setpoint u objetivo (150 °C por defecto).

**Cómo leerla:** al inicio, la temperatura sube rápidamente porque el error es grande y el controlador aplica potencia alta. A medida que se acerca al setpoint, la subida se suaviza. Idealmente, la curva azul converge a la verde y se mantiene estable.

Cuando ocurre una perturbación (botón "Abrir puerta"), aparece una **línea vertical roja punteada** marcando el momento exacto. Se puede observar la caída brusca de temperatura seguida de la recuperación automática.

Los tres comportamientos posibles son:

- *Solo Kp activo:* la curva azul se estabiliza ligeramente por debajo del setpoint (offset visible entre las dos líneas).
- *Kp + Ki activos:* la curva alcanza exactamente el setpoint, posiblemente con un pequeño sobrepaso antes de estabilizarse.
- *Kp + Ki + Kd activos:* la curva sube suavemente sin sobrepaso notable y se estabiliza con precisión.

### 2. Señal de control u(t) — potencia del calefactor

Muestra el porcentaje de potencia que el PID está ordenando al calefactor en cada instante.

**Cómo leerla:** al inicio, cuando el error es máximo (150 °C de diferencia), el controlador satura la potencia al 100 %. A medida que la temperatura se acerca al setpoint, la potencia baja gradualmente. En estado estable, la potencia se mantiene en un valor bajo positivo (suficiente para compensar las pérdidas de calor al ambiente).

Después de una perturbación, se observa un **pico de potencia** inmediato: el controlador detecta el nuevo error generado por la caída de temperatura y responde aumentando la potencia para recuperar el setpoint.

La línea horizontal punteada en 100 % representa el límite físico del calefactor. Si el controlador intenta aplicar más de 100 %, la señal se recorta (*clipping*), lo cual puede intensificar el windup integral.

### 3. Componentes P / I / D — contribución de cada término

Muestra las tres contribuciones por separado sobre el mismo eje:

- **Azul `P = Kp · e`:** sigue la forma del error. Grande al inicio, decrece al acercarse al setpoint.
- **Verde `I = Ki · ∫e`:** crece lentamente y de forma acumulativa. Al principio es casi cero, pero con el tiempo se vuelve el término dominante para eliminar el offset.
- **Naranja `D = Kd · de/dt`:** es grande en los momentos de cambio rápido (inicio, perturbaciones) y casi cero cuando el sistema está estable, porque la velocidad de cambio del error es mínima.

**Cómo leerla:** esta gráfica permite ver exactamente cuánto aporta cada término en cada momento y entender por qué el sistema se comporta como lo hace. Por ejemplo, si hay un overshoot, se puede observar que el término D debería ser negativo justo antes del pico (frenando), y si no lo es, Kd es demasiado bajo.

Después de una perturbación, el término D muestra un pico muy pronunciado porque el error cambia abruptamente, lo que refleja la detección inmediata del evento por parte del controlador.

### 4. Plano de fase — error vs velocidad de cambio del error

Esta gráfica, menos convencional pero muy informativa desde el punto de vista de sistemas complejos, muestra la trayectoria del sistema en el **espacio de estados** definido por:

- **Eje horizontal:** error actual `e(t) = setpoint - T(t)`
- **Eje vertical:** velocidad de cambio del error `de(t)/dt`

**Cómo leerla:** el punto de equilibrio deseado es el origen `(0, 0)`, que representa error cero y sin cambio en el error. Al inicio, el sistema está en la esquina superior derecha (error grande, error cambiando rápido). La trayectoria en espiral hacia el origen indica convergencia al equilibrio.

- Un sistema **bien sintonizado** produce una espiral suave que converge al origen sin rodeos innecesarios.
- Un sistema **subamortiguado** (Kd bajo, Ki alto) produce espirales amplias que rodean el origen varias veces antes de estabilizarse: esto corresponde a las oscilaciones visibles en la gráfica de temperatura.
- Cuando ocurre una **perturbación**, el punto sale del origen bruscamente y se puede observar la trayectoria completa de retorno: una curva que parte del nuevo error (grande y negativo), gira y converge de vuelta al origen.

Esta representación conecta directamente con el concepto de **atractor** de los sistemas complejos: el punto `(0, 0)` es el atractor del sistema, y toda la dinámica del controlador puede entenderse como el trabajo de llevar el estado del sistema hacia ese atractor y mantenerlo allí frente a perturbaciones.

---

## Por qué el sistema se regula solo

El principio fundamental detrás del PID es la **retroalimentación negativa**, que es el mecanismo de control más estudiado en cibernética desde los trabajos de Norbert Wiener y W. Ross Ashby.

El ciclo de retroalimentación opera de la siguiente forma en cada paso de tiempo:

```
Temperatura actual T(t)
        ↓
Error: e(t) = Setpoint − T(t)          ← comparación
        ↓
Controlador PID calcula u(t)            ← acción correctiva
        ↓
Calefactor aplica potencia u(t)
        ↓
Horno calienta → T(t) sube
        ↓
[volver al inicio]
```

La clave es que el error es la entrada del controlador y la temperatura (que el controlador afecta) es lo que determina el error. Esto crea un lazo cerrado: el sistema se observa a sí mismo y ajusta su comportamiento en función de qué tan lejos está del objetivo. No necesita intervención externa porque lleva incorporada la información de su propio estado.

Esto se distingue del **control en lazo abierto**, donde la potencia se fija de antemano sin mirar la temperatura resultante. En lazo abierto, si la puerta del horno se abre, la temperatura baja y el sistema no hace nada al respecto.

En términos de la **Ley de la Variedad Requerida de Ashby**: para controlar un sistema que puede encontrarse en muchos estados posibles (distintas temperaturas, distintos momentos de perturbación), el controlador necesita tener al menos la misma variedad de respuestas. El PID la logra combinando tres tipos de respuesta: proporcional al estado actual, integral al estado acumulado histórico, y derivativa al estado futuro anticipado.

---

## Cómo el sistema se recupera de perturbaciones

Una perturbación, en este simulador, es una caída brusca de 30 °C en la temperatura del horno (equivalente a abrir la puerta). Desde el punto de vista del controlador, lo que ocurre es lo siguiente:

**1. Detección inmediata por el término P.**  
En el instante en que la temperatura baja, el error `e(t)` salta de casi 0 a 30 °C. El término proporcional `Kp · e` responde instantáneamente con un aumento de potencia proporcional a ese error.

**2. Freno anticipatorio por el término D.**  
La velocidad de cambio del error `de/dt` es muy grande en el instante de la perturbación (el error cambia abruptamente). El término derivativo detecta esto y, durante la fase de recuperación, ayuda a no sobreapasar el setpoint al actuar como freno cuando la temperatura ya está subiendo rápido.

**3. Corrección acumulada por el término I.**  
Si la recuperación no es perfecta y queda un pequeño error residual, el término integral lo acumula y lo elimina con el tiempo.

**4. Convergencia al atractor.**  
En la gráfica del plano de fase, este proceso es completamente visible: la perturbación saca al sistema del origen, y la trayectoria describe una curva que regresa al punto `(0, 0)`. La velocidad y suavidad de esa curva depende directamente de los valores de Kp, Ki y Kd.

El sistema no necesita que un operador ajuste nada. La retroalimentación continua garantiza que cualquier desviación del setpoint, sin importar cuándo ocurra, genere automáticamente una respuesta correctiva. Esta propiedad se conoce como **regulación automática** y es el objetivo central del diseño de controladores en ingeniería de sistemas.

---

## Experimentos sugeridos

Estos experimentos permiten observar el efecto individual de cada componente del PID:

**Experimento 1 — El problema del offset (solo P):**  
Poner `Ki = 0`, `Kd = 0` y dejar solo `Kp = 2.0`. Observar que la temperatura se estabiliza algunos grados por debajo de 150 °C. Ese hueco persistente es el offset, y demuestra que la acción proporcional sola es insuficiente para control preciso.

**Experimento 2 — Eliminación del offset con I:**  
Con el sistema del experimento anterior, subir `Ki` lentamente desde 0. Observar cómo la temperatura termina alcanzando exactamente 150 °C. Subir `Ki` demasiado produce oscilaciones (*windup*).

**Experimento 3 — Control del overshoot con D:**  
Con `Kp` alto (por ejemplo 5.0) y `Ki = 0.05`, observar que la temperatura se pasa del setpoint antes de estabilizarse. Subir `Kd` y observar cómo ese sobrepaso se reduce.

**Experimento 4 — Respuesta a perturbaciones:**  
Con el sistema estable en 150 °C (parámetros por defecto), presionar "Perturbación" y observar la caída y recuperación. Luego repetir con `Kd = 0` y comparar: sin término derivativo, la recuperación puede tener más overshoot.

**Experimento 5 — Cambio de setpoint en caliente:**  
Con el sistema estable, mover el slider de setpoint a 200 °C. El PID reacciona como si fuera una perturbación: detecta el nuevo error y lleva el sistema al nuevo objetivo sin reiniciar.

---

## Estructura del proyecto

```
pid_horno.py      # Código fuente principal con simulación y visualización
README.md         # Este documento
```

---

## Dependencias

| Librería | Versión mínima | Uso |
|----------|----------------|-----|
| `numpy`  | 1.20           | Integración numérica y cálculo de gradientes |
| `matplotlib` | 3.4       | Visualización interactiva y animación |

---

## Referencias

- Wiener, N. (1948). *Cybernetics: Or Control and Communication in the Animal and the Machine*. MIT Press.
- Ashby, W. R. (1956). *An Introduction to Cybernetics*. Chapman & Hall.
- Åström, K. J., & Hägglund, T. (1995). *PID Controllers: Theory, Design, and Tuning*. ISA Press.
- Bar-Yam, Y. (1997). *Dynamics of Complex Systems*. Addison-Wesley.
