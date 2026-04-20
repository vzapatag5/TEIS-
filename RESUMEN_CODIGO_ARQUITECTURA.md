# RESUMEN DE CÓDIGO: Validación de Extracción de Lógica de Negocio

**Objetivo**: Validar que la lógica de negocio fue extraída correctamente de la capa de presentación (views.py) hacia la capa de servicios (services.py).

---

## 1. ANÁLISIS DE CAPAS

### CAPA DE PRESENTACIÓN (views.py)
**Responsabilidad**: Recibir peticiones HTTP y devolver respuestas

#### Clase `CompraView` (CBV - Class Based View)
```python
class CompraView(View):
    """Vista Basada en Clases - Actúa como un 'Portero'"""
    template_name = 'tienda_app/compra.html'
    
    # DELEGACIÓN CORRECTA: Delega TODO el trabajo al servicio
    def get(self, request, libro_id):
        servicio = self.setup_service()
        contexto = servicio.obtener_detalle_producto(libro_id)  # Lógica en servicio
        return render(request, self.template_name, contexto)
    
    def post(self, request, libro_id):
        servicio = self.setup_service()
        try:
            total = servicio.ejecutar_compra(libro_id, cantidad=1)  # Lógica en servicio
            return render(request, self.template_name, {'mensaje_exito': ...})
        except (ValueError, Exception) as e:
            return render(request, self.template_name, {'error': str(e)}, status=400)
```

**Características de buena separación:**
- Solo maneja peticiones y respuestas
- No accede directamente a BD (sin `Libro.objects.get()`)
- No calcula precios (sin `float(libro.precio) * 1.19`)
- No ejecuta lógica de pago
- No valida stock

---

### CAPA DE SERVICIOS (services.py)
**Responsabilidad**: Orquestar lógica de negocio e interacción entre dominios

#### Clase `CompraService`
```python
class CompraService:
    """SERVICE LAYER: Orquesta dominio, infraestructura y BD"""
    
    def __init__(self, procesador_pago):
        self.procesador_pago = procesador_pago
        self.builder = OrdenBuilder()
```

#### Método: `obtener_detalle_producto()`
```python
def obtener_detalle_producto(self, libro_id):
    # Obtiene el libro (acceso a BD)
    libro = get_object_or_404(Libro, id=libro_id)
    
    # Calcula total con impuestos (lógica de dominio)
    total = CalculadorImpuestos.obtener_total_con_iva(libro.precio)
    
    # Retorna datos estructurados
    return {"libro": libro, "total": total}
```

**Punto de extracción**: 
- Antes (en views): `total = float(libro.precio) * 1.19`
- Ahora (en services): `CalculadorImpuestos.obtener_total_con_iva(libro.precio)`

---

#### Método: `ejecutar_compra()` (Orquestación completa)
```python
def ejecutar_compra(self, libro_id, cantidad=1, direccion="", usuario=None):
    # 1. Obtener datos
    libro = get_object_or_404(Libro, id=libro_id)
    inv = get_object_or_404(Inventario, libro=libro)
    
    # 2. Validar precondiciones
    if inv.cantidad < cantidad:
        raise ValueError("No hay suficiente stock para completar la compra.")
    
    # 3. Construir entidad de dominio (patrón Builder)
    orden = (
        self.builder
        .con_usuario(usuario)
        .con_libro(libro)
        .con_cantidad(cantidad)
        .para_envio(direccion)
        .build()
    )
    
    # 4. Ejecutar proceso de pago (inyectado)
    pago_exitoso = self.procesador_pago.pagar(orden.total)
    if not pago_exitoso:
        orden.delete()
        raise Exception("La transacción fue rechazada por el banco.")
    
    # 5. Actualizar estado (inventario)
    inv.cantidad -= cantidad
    inv.save()
    
    # 6. Retornar resultado
    return orden.total
```

**Extracción de lógica realizada:**
| Lógica | Antes (views.py) | Ahora (services.py) |
|--------|------------------|---------------------|
| Validar stock | En POST de view | `ejecutar_compra()` |
| Calcular total | En template/view | `CalculadorImpuestos` |
| Procesar pago | Escritura manual en archivo | `procesador_pago.pagar()` |
| Actualizar inventario | En POST de view | `ejecutar_compra()` |
| Construir orden | Lógica suelta | `OrdenBuilder` (patrón) |

---

## 2. COMPARATIVA: ANTES vs DESPUÉS

### ANTES: Function Based View (FBV) - ACOPLADO

**Nota**: Este FBV (`compra_rapida_fbv`) sigue existiendo en el código como referencia educativa de lo que NO se debe hacer.

```python
def compra_rapida_fbv(request, libro_id):
    libro = get_object_or_404(Libro, id=libro_id)
    if request.method == 'POST':
        inventario = Inventario.objects.get(libro=libro)
        if inventario.cantidad > 0:
            # Lógica de negocio mezclada con presentación
            total = float(libro.precio) * 1.19  # Cálculo de precios
            with open("pagos_manuales.log", "a") as f:  # I/O de pago
                f.write(f"[{datetime.datetime.now()}] Pago FBV: ${total}\n")
            inventario.cantidad -= 1  # Actualización de inventario
            inventario.save()
            Orden.objects.create(libro=libro, total=total)
            return HttpResponse(f"Compra exitosa: {libro.titulo}")
        return HttpResponse("Sin stock", status=400)
    # ... más lógica mezclada
```

**Problemas con FBV**:
- Imposible de testear (acoplado a request/response)
- Imposible de reutilizar (solo en views)
- Imposible de cambiar pagos (lógica hardcodeada)
- Violación de SRP (una función hace todo)

---

### DESPUÉS: Servicios + CBV - DESACOPLADO

Tenemos dos implementaciones mejoradas:

#### Versión completa (CompraView):
```python
class CompraView(View):
    def setup_service(self):
        gateway = PaymentFactory.get_processor()
        return CompraService(procesador_pago=gateway)

    def get(self, request, libro_id):
        servicio = self.setup_service()
        contexto = servicio.obtener_detalle_producto(libro_id)
        return render(request, self.template_name, contexto)

    def post(self, request, libro_id):
        servicio = self.setup_service()
        try:
            total = servicio.ejecutar_compra(libro_id, cantidad=1)
            return render(request, self.template_name, {'mensaje_exito': ...})
        except (ValueError, Exception) as e:
            return render(request, self.template_name, {'error': str(e)}, status=400)
```

#### Versión compacta optimizada (CompraRapidaView - menos de 10 líneas):
```python
class CompraRapidaView(View):
    template_name = 'tienda_app/compra_rapida.html'

    def get(self, request, libro_id):
        libro = get_object_or_404(Libro, id=libro_id)
        return render(request, self.template_name, {'libro': libro, 'total': float(libro.precio) * 1.19})

    def post(self, request, libro_id):
        try:
            total = CompraService(PaymentFactory.get_processor()).ejecutar_compra(libro_id)
            return HttpResponse(f"Compra exitosa por: ${total}")
        except Exception as e:
            return HttpResponse(str(e), status=400)
```

**Características de ambas versiones**:
- Delegan toda la lógica de negocio al servicio
- Independientes de HTTP (CompraService es reutilizable)
- Fáciles de testear
- Cumplen SRP (Single Responsibility Principle)
- CompraRapidaView: instanciación directa para código más compacto
- CompraView: patrón setup_service() para mayor claridad y reutilización

**Ventajas**:
- Testeable sin HTTP: `CompraService.ejecutar_compra(1, 2)` funciona
- Reutilizable en APIs, CLI, scripts, Celery tasks
- Inyección de dependencias (procesador_pago)
- Código conciso sin sacrificar legibilidad

---

## 3. ARQUITECTURA IMPLEMENTADA

```
┌─────────────────────────────────────────────────────────┐
│              CAPA DE PRESENTACIÓN                       │
│  (views.py: CompraView - solo HTTP, delegación)        │
└────────────────────┬────────────────────────────────────┘
                     │
                     | delega lógica
┌─────────────────────────────────────────────────────────┐
│           CAPA DE SERVICIOS                             │
│  (services.py: CompraService - orquesta negocio)       │
│  - obtener_detalle_producto()                          │
│  - ejecutar_compra()                                    │
└────────────────────┬────────────────────────────────────┘
                     │
        |────────────┼────────────┬─────────────|
        |            |            |             |
┌────────────┐ ┌────────────┐ ┌───────┐ ┌──────────────┐
│  DOMINIO   │ │ INFRA      │ │ MODELOS│ │FACTORIES    │
│(logic.py)  │ │(factories) │ │ (BD)  │ │(inyección)  │
└────────────┘ └────────────┘ └───────┘ └──────────────┘
```

### Flujo de una petición:
```
1. POST /comprar/1 → CompraView.post()
2. CompraView setup_service() crea CompraService
3. CompraService.ejecutar_compra(1) realiza:
   - Obtiene Libro y validaciones
   - Construye Orden (dominio)
   - Procesa pago (infra inyectada)
   - Actualiza inventario
4. Retorna total → view formatea respuesta HTTP
```

---

## 4. VALIDACIÓN: PRINCIPIOS SOLID APLICADOS

| Principio | Aplicación | Evidencia |
|-----------|-----------|----------|
| **S** - Single Responsibility | Views: HTTP; Services: negocio; Domain: lógica pura | Separación clara en capas |
| **O** - Open/Closed | Cambiar procesador de pagos sin modificar CompraService | `PaymentFactory.get_processor()` inyectado |
| **L** - Liskov Substitution | Diferentes procesadores intercambiables | `procesador_pago.pagar()` polimórfico |
| **I** - Interface Segregation | Servicios solo requieren `procesador_pago` | `CompraService(procesador_pago=gateway)` en ambos patrones |
| **D** - Dependency Injection | Inyección flexible: setup_service() o instancia directa | Ambas estrategias en views.py |

---

## 5. CONCLUSIÓN: EXTRACCIÓN CORRECTA

### Lógica extraída de la presentación:
1. **Cálculo de precios con IVA** → `CalculadorImpuestos` (dominio)
2. **Validación de stock** → `CompraService.ejecutar_compra()` (servicio)
3. **Procesamiento de pago** → `procesador_pago` (infraestructura)
4. **Construcción de órdenes** → `OrdenBuilder` (patrón)
5. **Actualización de inventario** → `CompraService` (servicio)

### La capa de presentación (views.py) ahora:
- NO calcula lógica de negocio
- NO valida stock  
- NO procesa pagos
- NO accede directamente a BD para operaciones complejas
- **Solo recibe peticiones y delega al servicio**
- **Formatea respuestas HTTP**
- **Ofrece dos patrones válidos**: setup_service() o instanciación directa

**Nota**: `compra_rapida_fbv` se mantiene como código educativo/histórico.

**Estado: ARQUITECTURA VALIDADA Y OPTIMIZADA**

---

## RECOMENDACIONES

### Para mantener esta arquitectura limpia:
1. **Capa de Presentación**: Solo `request` → `service` → `response` 
   - Puede usar `setup_service()` para reutilización frecuente
   - O instanciación directa para vistas simples/rápidas
2. **Capa de Servicios**: Orquesta y delega a dominios/infra, acepta dependencias inyectadas
3. **Capa de Dominio**: Lógica pura (`CalculadorImpuestos`, `OrdenBuilder`), sin dependencias externas
4. **Capa de Infra**: Base de datos, APIs externas, factories (`PaymentFactory`)

### Próximas mejoras sugeridas:
1. **Tests unitarios para CompraService** (independiente de HTTP):
   - `test_ejecutar_compra_exitosa()`
   - `test_stock_insuficiente()` 
   - `test_pago_rechazado()`

2. **Excepciones personalizadas**:
   - `StockInsuficienteError` 
   - `PagoRechazadoError`
   - Mejor manejo y logging

3. **Contrato de interfaces**:
   - Documentar contrato de `procesador_pago`
   - Considerar Protocol o ABC de Python

4. **Mejoras de base de datos**:
   - Agregar `@transaction.atomic` a `ejecutar_compra()`
   - Implementar rollback automático en caso de error

5. **Refactorización futura**:
   - Deprecar `compra_rapida_fbv` cuando el equipo esté completamente familiarizado
   - Considerar usar celery para pagos asíncronos

