from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django.shortcuts import get_object_or_404
from tienda_app.infra.factories import PaymentFactory
from tienda_app.services import CompraService
from tienda_app.models import Libro  # <-- importar el modelo

from .serializers import OrdenInputSerializer


class CompraAPIView(APIView):
    """
    Endpoint para procesar compras via JSON.
    POST /api/v1/comprar/
    Payload: {"libro_id": 1, "direccion_envio": "Calle 123", "cantidad": 1}
    """

    def post(self, request):
        serializer = OrdenInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        datos = serializer.validated_data

        try:
            # Buscar el objeto Libro real (no un dict)
            libro = get_object_or_404(Libro, id=datos['libro_id'])

            gateway = PaymentFactory.get_processor()
            servicio = CompraService(procesador_pago=gateway)
            usuario = request.user if request.user.is_authenticated else None

            # Pasar objetos Libro, que es lo que espera el builder
            lista_productos = [libro] * datos.get('cantidad', 1)

            resultado = servicio.ejecutar_proceso_compra(
                usuario=usuario,
                lista_productos=lista_productos,
                direccion=datos['direccion_envio'],
            )

            return Response(
                {'estado': 'exito', 'mensaje': resultado},
                status=status.HTTP_201_CREATED,
            )

        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': 'Error interno'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)