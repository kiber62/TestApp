from django.db import models
from django.contrib.auth.models import User
from datetime import datetime

class Order(models.Model):

    client_id = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Заказчик', blank=True)
    date_order = models.DateTimeField(verbose_name='Дата заказа')
    total = models.DecimalField(verbose_name='Сумма заказа', decimal_places=2, max_digits=100)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ("-date_order", "id")



    def __str__(self):
        return f'Заказ № {self.id}'
