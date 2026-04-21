from django.urls import path
from .api.views import CompraAPIView, ProductosAPIView
from .views import CompraView, compra_rapida_fbv, CompraRapidaView

urlpatterns = [
    path('compra/<int:libro_id>/', CompraView.as_view(), name='finalizar_compra'),
    path('api/v1/comprar/', CompraAPIView.as_view(), name='api_comprar'),
    path('fbv/<int:libro_id>/', compra_rapida_fbv, name='compra_fbv'),
    path('rapida/<int:libro_id>/', CompraRapidaView.as_view(), name='compra_rapida'),
    path('api/v1/productos/', ProductosAPIView.as_view(), name='api_productos'),
]