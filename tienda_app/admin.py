from django.contrib import admin
from .models import Libro, Orden, Inventario

admin.site.register(Libro)
admin.site.register(Orden)
admin.site.register(Inventario)