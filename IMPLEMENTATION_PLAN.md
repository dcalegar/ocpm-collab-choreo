# Plan de implementación del núcleo neutral

## Objetivo

Implementar el rediseño en el branch `redesign/unified-neutral-core`: reemplazar
`ChoreographyMessage` y los mensajes por observación del núcleo por un único
`Message` lógico, incorporar roles y endpoints explícitos, y mantener
compatibilidad mediante los adaptadores $\alpha_C$ y $\eta_H$.

## Estado

- [x] Punto 1: modelo fuente y construcción del núcleo neutral.
- [x] Punto 2: adaptador InfSys $\alpha_C$.
- [ ] Punto 3: índices, serialización y criterios.
- [ ] Punto 4: adaptadores Hobeck.
- [ ] Punto 5: predicción.
- [ ] Punto 6: experimentos y documentación.

## 1. Actualizar el modelo fuente y el núcleo

- Extender `ExchangeEvent` con roles explícitos de la tarea y endpoints
  explícitos de la response. `None` indica que la fuente no los declara y que
  se aplica el fallback documentado.
- Mantener `sender` y `receivers` como endpoints del request.
- Ejecutar M1--M8, pero retirar del núcleo los objetos `Message` por
  observación y sus relaciones.
- Crear únicamente objetos lógicos de tipo `Message`:
  - `message::<caso>::<clave>`;
  - `message::@<evento>`;
  - `message::@<evento>::response`.
- Relacionar directamente cada send/receive mediante E2O `send`/`receive`.
- Agregar O2O `source`, `target` y `exchanged_in`.
- Agregar E2O `initiator` y `participant` desde la tarea.
- Dar singleton también a receives sin clave; un intercambio bidireccional sin
  claves crea dos.
- Mantener diagnósticos de nombres, contenidos y claves incompatibles, sin
  reparar los datos.

### Resultado del punto 1

- `ExchangeEvent` distingue endpoints del request, roles declarados y
  endpoints declarados de la response. `None` activa el fallback; una tupla
  vacía conserva una afirmación explícitamente vacía.
- El núcleo elimina los `msg::<evento>` de M4 y genera solamente objetos
  lógicos `Message` con los identificadores acordados.
- Send y receive se relacionan directamente con el mensaje lógico; los
  endpoints y el caso se almacenan como `source`, `target` y `exchanged_in`.
- Las tareas almacenan `initiator` y `participant`. Para una tarea cuyo carrier
  es un send, los participantes se obtienen de todos los targets del request,
  incluidos receives correlacionados y multicast que el send no declara.
- Se conservan temporalmente alias de constantes antiguas y el resultado
  InfSys original dentro de `UnifiedResult`; no forman parte del núcleo y se
  retirarán cuando sus consumidores hayan sido migrados.
- Validación al cerrar el punto: 22 pruebas de mapping/experimentos pasan; 24
  pruebas de predicción pasan y una queda omitida por depender de outputs
  regenerados.
- Comprobación adicional en memoria sobre Artificial1: los perfiles CL, ChL y
  completo contienen exclusivamente identificadores `message::`, todo evento
  send/receive tiene exactamente una relación directa y todo mensaje tiene un
  único `exchanged_in`; no se regeneraron aún los archivos `mapped/`.

## 2. Construir el adaptador InfSys $\alpha_C$

- Crear un adaptador separado que lea exclusivamente las tablas del núcleo.
- Seleccionar eventos locales y reconstruir para cada send/receive el objeto
  `Message` `msg::<evento>`, sus relaciones E2O/O2O legacy y sus atributos.
- Eliminar eventos, objetos y relaciones exclusivos de coreografía.
- Persistir la vista como `<out>_infsys.sqlite`.
- Mantener la normalización del espacio no separable de Real4 únicamente en E1.
- No usar `UnifiedResult.infsys` para construir la vista: reconstruirla desde
  las tablas neutrales. Usar ese valor temporal solamente como oráculo unitario
  para exigir igualdad de tablas con `cx.transform`.
- Reconstruir `from`/`to` por observación a partir de los atributos preservados
  en cada evento, no a partir del endpoint agregado del mensaje lógico.

### Resultado del punto 2

- `source/mapping/export_infsys.py` implementa $\alpha_C$ sobre las cuatro
  tablas del núcleo y devuelve un `cx.TransformResult`, de modo que P1.1--P1.6
  y los exportadores InfSys se aplican sin cambios en el punto 3.
- Selección: eventos con `in_collaboration`; E2O `in_collaboration`,
  `in_orchestration` e `in_participant`; O2O `part_of`/`for_participant` de los
  `OrchestrationCase`; objetos alcanzados desde ellos y objetos del núcleo sin
  ninguna relación. Estos últimos solo pueden provenir de M1--M8 (p. ej., un
  participante registrado como endpoint de un evento `task`, que M8 no
  preserva), porque todo objeto agregado por M10--M13 está relacionado.
- Cada E2O `send`/`receive` de un evento local da un `msg::<evento>` con
  `sender`/`receiver` y `from`/`to` tomados de `fromParticipant`/`toParticipant`
  del propio evento, y `exchanged_in` desde su `in_collaboration`. τ se
  reconstruye registrando los participantes retenidos en orden y se exige que
  coincida con el tipo almacenado.
- `map_log.write_outputs` persiste `<out>_infsys.sqlite` con los testigos de
  exportación de InfSys calculados sobre la vista, solo si hay eventos locales,
  y registra sus estadísticas en `export.infsys_view` de `_checks.json`.
- Corrección en el núcleo: `map_log` extendía en el lugar el `ParticipantTypes`
  de `UnifiedResult.infsys`; ahora trabaja sobre una copia, de modo que el
  oráculo queda intacto.
- Validación al cerrar el punto: 47 pruebas de mapping/experimentos pasan (25
  nuevas en `tests/test_export_infsys.py`: igualdad con `cx.transform` en
  tablas, dtypes, estadísticas y τ; independencia de `UnifiedResult.infsys`;
  endpoints por observación; vista vacía sin eventos locales; SQLite igual a la
  exportación InfSys). En memoria, $\alpha_C(\mu_U(L))$ es igual a
  `cx.transform` en las 29 ejecuciones XES con eventos locales del corpus.
  Los `<out>_infsys.sqlite` regenerados son iguales a las 9 referencias InfSys
  de E1 sin proyección (Real4, con la normalización documentada de E1).
- Pendiente para el punto 3: `export_relations()` y P1 siguen usando
  `UnifiedResult.infsys`; E1 sigue leyendo la proyección del núcleo. U2 y U3
  fallan en los perfiles con eventos de mensaje ya desde el punto 1, porque
  `Index` aún no lee las E2O directas. No se ejecutaron las pruebas de
  predicción (no hay `.venv-predict`) ni los logs Ethereum (no hay clon de
  ocelchor).

## 3. Actualizar índices, serialización y criterios

- Obtener mensajes por E2O `send`/`receive` y endpoints por `source`/`target`.
- Separar las aristas testigo del núcleo de las de $\alpha_C$.
- Evaluar P1.1--P1.6 sobre $\alpha_C(\mu_U(L))$ y P1.7 sobre ambas
  serializaciones.
- Reformular U3--U6 y agregar U8 para identidad, endpoints, roles y estados de
  correlación.
- Tratar U1, U2, U3, U5 y U7 como estructurales; U4, U6 y U8 como diagnósticos.
- Migrar `Index.message_events()` a las relaciones E2O directas y eliminar los
  alias transitorios `OT_CM`, `Q_SENT_AS`, `Q_RECEIVED_AS`, `Q_FROM` y `Q_TO`
  cuando ya no tengan consumidores.
- Reemplazar `export_relations()`: actualmente agrega testigos calculados sobre
  `UnifiedResult.infsys`, que pueden apuntar a los `msg::<evento>` retirados.
  El núcleo debe calcular testigos solo sobre sus propias tablas; $\alpha_C$
  debe calcular los suyos por separado.
- Reemplazar la proyección estructural de E1: `NEW_OBJECT_TYPES` contiene ahora
  `Message`, por lo que proyectar por tipo eliminaría también los mensajes que
  deben reconstruirse. E1 debe leer exclusivamente `<out>_infsys.sqlite`.
- Hacer que P1.7 rechace cualquier E2O cuyo objeto no exista, además de comprobar
  alcance, para detectar inmediatamente testigos legacy inválidos.

## 4. Actualizar los adaptadores Hobeck

- Hacer que $\eta_H$ exporte roles almacenados, endpoints `source`/`target` y
  endpoints explícitos de la response, sin recalcularlos.
- Hacer que $\iota_H$ preserve roles y endpoints aunque discrepen.
- Rechazar únicamente una clasificación ambigua de request/response u otra
  pérdida real de información.
- Cambiar E2b para que las discrepancias sobrevivan al ida y vuelta y sean
  reportadas por U8.

## 5. Adaptar las predicciones

- Cambiar el tipo de mensaje de E4 a `Message`.
- Leer `initiator`/`participant` para la tarea y `source`/`target` para los
  mensajes.
- Filtrar E2O `initiator`/`participant` en una copia temporal antes de delegar
  el SQLite a OCPA, sin modificar `ocpm-collab-ppm`.
- Comprobar en Healthcare 100 ejecuciones y 5,5 eventos por ejecución, no 550.

## 6. Actualizar experimentos y documentación

- E1 compara `<out>_infsys.sqlite` con las referencias InfSys.
- E2/E2b validan $\eta_H$ y el ida y vuelta; E3 reporta P1, U1--U8 y C0--C16;
  E4 vuelve a ejecutar las diez tareas.
- Regenerar outputs no versionados y resultados versionados.
- Actualizar los README y `mapping_unified_analysis.tex` solamente después de
  completar la revalidación.

## Validación final

1. Ejecutar tests de mapping y experimentos.
2. Ejecutar tests de predicción.
3. Regenerar con `map_all.py`.
4. Ejecutar E1, E2, E2b y E3.
5. Ejecutar E4 con el entorno de predicción.

La implementación se acepta cuando todos los tests pasan, E1 obtiene igualdad,
E2/E2b mantienen la equivalencia prevista, ningún criterio estructural falla y
E4 termina de extremo a extremo sin modificar el repositorio InfSys.

## Restricciones

- Trabajar únicamente en `redesign/unified-neutral-core`.
- Considerar `data/*/mapped/` regenerable.
- Sincronizar el documento del artículo después de validar completamente el
  código.
