import datetime
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.http import HttpResponse

from .infra.factories import PaymentFactory
from .services import CompraService
from .models import Libro, Inventario, Orden


class CompraView(View):
    """
    CBV: Vista Basada en Clases.
    Actúa como un "Portero": recibe la petición y delega al servicio.
    """

    template_name = "tienda_app/compra.html"

    def setup_service(self):
        gateway = PaymentFactory.get_processor()
        return CompraService(procesador_pago=gateway)

    def get(self, request, libro_id):
        servicio = self.setup_service()
        contexto = servicio.obtener_detalle_producto(libro_id)
        return render(request, self.template_name, contexto)

    def post(self, request, libro_id):
        servicio = self.setup_service()
        libro = get_object_or_404(Libro, id=libro_id)
        usuario = request.user if request.user.is_authenticated else None
        try:
            mensaje = servicio.ejecutar_proceso_compra(
                usuario=usuario,
                lista_productos=[libro],
                direccion=request.POST.get("direccion", ""),
            )
            return render(
                request,
                self.template_name,
                {
                    "mensaje_exito": mensaje,
                },
            )
        except (ValueError, Exception) as e:
            return render(request, self.template_name, {"error": str(e)}, status=400)


# ── PASO 1: FBV Spaghetti ──────────────────────────────────────────
def compra_rapida_fbv(request, libro_id):
    libro = get_object_or_404(Libro, id=libro_id)
    if request.method == "POST":
        inventario = Inventario.objects.get(libro=libro)
        if inventario.cantidad > 0:
            total = float(libro.precio) * 1.19
            with open("pagos_manuales.log", "a") as f:
                f.write(f"[{datetime.datetime.now()}] Pago FBV: ${total}\n")
            inventario.cantidad -= 1
            inventario.save()
            Orden.objects.create(libro=libro, total=total)
            return HttpResponse(f"Compra exitosa: {libro.titulo}")
        return HttpResponse("Sin stock", status=400)
    total_estimado = float(libro.precio) * 1.19
    return render(
        request,
        "tienda_app/compra_rapida.html",
        {"libro": libro, "total": total_estimado},
    )


# ── PASO 2: CBV Mejorada (menos de 10 líneas) ─────────────────────
class CompraRapidaView(View):
    template_name = "tienda_app/compra_rapida.html"

    def get(self, request, libro_id):
        libro = get_object_or_404(Libro, id=libro_id)
        return render(
            request,
            self.template_name,
            {"libro": libro, "total": float(libro.precio) * 1.19},
        )

    def post(self, request, libro_id):
        try:
            total = CompraService(PaymentFactory.get_processor()).ejecutar_compra(
                libro_id
            )
            return HttpResponse(f"Compra exitosa por: ${total}")
        except Exception as e:
            return HttpResponse(str(e), status=400)
