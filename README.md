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



