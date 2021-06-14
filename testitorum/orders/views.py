from django.shortcuts import render, redirect
from django.db.models import Sum
from django.http import JsonResponse, HttpResponse, Http404
from django.core import serializers
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.utils.timezone import make_aware
from django.contrib.auth import authenticate


from datetime import datetime, timedelta
from typing import Tuple
import time
import re
import base64

from .models import Order


###########################################################
# Вспомогательные функции

def make_date_zone(naive_datetime: datetime) -> datetime:
    """
    Приведение дат без TimeZone, к датам с явным указанием TimeZone.
    Данные TimeZone берутся из настроек Django.
    :param naive_datetime: Дата без TimeZone
    :return: Дата с TimeZone
    """
    return make_aware(naive_datetime)


def days_for_week(number_week: int, year: int = 2021) -> list:
    """
    Нахождение всех дней по номеру недели и году.
    :param year: Год ( например 2021)
    :param number_week: Номер недели (например 23)
    :return: dates_of_week Массив дат с понедельника по воскресенье
    """

    dates_of_week: list = []

    # Находим дату первого деня недели
    # 1 - то понедельник, 0 - воскресенье
    first_day_week: int = 1
    startdate = time.asctime(time.strptime('%i %d %d' % (year, number_week, first_day_week), '%Y %W %w'))
    startdate = datetime.strptime(startdate, '%a %b %d %H:%M:%S %Y')

    # Заносим первую дату недели в выходной список
    dates_of_week.append(startdate)

    for i in range(1, 7):
        day = startdate + timedelta(days=i)
        dates_of_week.append(day)

    return dates_of_week


def determining_year_week() -> Tuple[int, int]:
    """
    Определение сегодняшней недели, года
    :return: Сегодняшняя неделя, год
    """
    now: datetime
    week: int
    year: int

    # Сегодняшняя дата
    now_moment = datetime.now()

    # Сегодняшняя неделя
    week = now_moment.isocalendar()[1]

    # Сегодняшний год
    year = now_moment.isocalendar()[0]

    return (year, week)


def add_order(id: str, total: str) -> None:
    """
    Добавление нового заказа
    :param id: ID заказчика
    :param total: Сумма
    """
    if id.replace(' ', '') == '' or total.replace(' ', '') == '':
        return

    date_order: datetime = datetime.now()

    # Проверка что ID - чиcло
    if id.isdigit():
        client_id = User.objects.get(id=id)

        if not client_id.groups.filter(name='Заказчики').exists():
            return

    # Проверяем что TOTAL
    if not total.replace('.', '', 1).isdigit():
        return

    # Приводим строку к числовому значению и округляем до 2х знаков после запятой
    total = round(float(total), 2)

    # Добавление нового заказа
    try:
        Order.objects.create(client_id=client_id, date_order=date_order, total=total)
    except:
        pass

    return


# Конец вспомогательных функций
###########################################################


def index(request) -> HttpResponse:
    """
    Главная страница
    """

    pattern: str = '^(\d{4})-W(\d{2})$' # Паттерн для проверки строки из input type=week
    orders: Order = Order.objects.all() # Получение всех заказов
    week_data: list = []
    dates_week: list

    # Статистические данные
    total_for_week: int = 0      # Сумма заказов за один день
    client_for_week: set = set() # Список заказчиков за один день

    # Данные о сегодняшнем годе и недели
    week: int = determining_year_week()[1]        # Сегодняшняя неделя
    year: int = determining_year_week()[0]        # Сегодняшний год
    year_and_week_string: str = f'{year}-W{week}' # Строка для input type=week, a формате 2021-W23

    # Проверка на данные из формы по выбору недели
    # для отображения данных, за указанную неделю
    if request.method == 'POST':

        # Проверка что есть данные в поле week_id,
        # и нет данных с скрытом поле week_id2 (для защиты)
        if request.POST['week_id'] and request.POST['week_id2'] == '':
            year_and_week_string_source = request.POST['week_id']

            # Проверка, что строка из поля week_id соответствует заданному шаблону,
            # в противном случае год и неделя будут сегодняшние
            if re.match(pattern=pattern, string=year_and_week_string_source):
                year_and_week_string = year_and_week_string_source
                year = int(re.match(pattern=pattern, string=year_and_week_string).groups()[0])
                week = int(re.match(pattern=pattern, string=year_and_week_string).groups()[1])

    # Находим все дни недели по заданному году и номеру недели
    dates_week = days_for_week(year=year, number_week=week)

    # Проходим каждый день в цикле, для сбора
    # статистических данных за каждый день (заказчики и суммы за день)
    for start_date in dates_week:
        start_date: datetime # Начало дня 00:00:00
        end_date: datetime   # Конец дня 23:59:59

        # Расчитываем конец дня
        end_date = start_date + timedelta(hours=23, minutes=59, seconds=59)

        # Приведение дат без TimeZone, к датам с явно указанной TimeZone
        start_date = make_date_zone(start_date)
        end_date = make_date_zone(end_date)

        # Фильтрация из общего списка всех заказов,
        # по началу и концу дня
        orders_day = orders.filter(date_order__range=(start_date, end_date))

        # Получение данных о заказчиках за выбранный день
        if len(orders_day) > 0:
            # Из полученного (отфильтрованного) списка получаем ВСЕХ заказчиков
            users = [f'{order.client_id.last_name} {order.client_id.first_name}' for order in orders_day]

            # Убираем дублируемых заказчиков
            users = set(users)
        else:
            users = set()

        # Получение данных о суммах заказов за выбранный день
        if len(orders_day) > 0:
            sum = orders_day.aggregate(Sum('total'))
            sum_total = float(sum['total__sum'])
        else:
            sum_total = 0

        # Добавление данных в итоговую информацию за день
        total_for_week += sum_total                # Сумирование по дням
        client_for_week = client_for_week | users  # Объединение всех заказчиков по дням

        # Формирование данных за один день
        day_data = {
            "day": start_date.strftime("%d.%m.%Y"),
            "clients": ', '.join(list(users)),
            "total": sum_total
        }

        # Добавление данных за конкретный день в сфодную информацию за всю неделю
        week_data.append(day_data)

    # Делаем пагинацию для всего списка по 10 записей
    paginator = Paginator(orders, 10)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'orders/index.html', {"page_obj": page_obj, "week": year_and_week_string,
                                                 "week_data": week_data, "total_for_week": round(total_for_week, 2),
                                                 "client_for_week": ', '.join(list(client_for_week)),
                                                 "active_page":"index"})


def my_orders(request) -> HttpResponse:
    """
    Страница администратора
    """

    if not request.user.is_authenticated:
        return redirect('home')

    if not request.user.is_staff:
        return redirect('logout')

    # Список заказов для таблицы,
    # отсотрированно по фамилии и имени
    dataOrders: Order = Order.objects.all().order_by('id')

    # Список заказчиков для формы выбора Заказчмка,
    # отсотрированно по фамилии и имени
    users: User = User.objects.filter(groups__name='Заказчики').order_by("last_name", "first_name")

    # Проверяем что пришли данные из форм
    if request.method == 'POST':

        # Проверка скрытого "пустого" поля
        if request.POST['type_form1'] == '':

            # Данные из кнопки (формы) удаления заказа
            if request.POST['type_form'] == 'delete_order':

                # Получаем ID удаляемого заявления
                id = request.POST['order_id']

                # Проверка что ID - чиcло
                if id.isdigit():
                    try:
                        Order.objects.get(id=id).delete()
                    except:
                        pass

            # Данные из формы добавления заказа
            elif request.POST['type_form'] == 'new_order':
                # Получаем ID заказчика
                id_user = request.POST['user']
                total_order = request.POST.get("total_order")

                add_order(id=id_user, total=total_order)


    # Делаем пагинацию для всего списка по 10 записей
    paginator = Paginator(dataOrders, 10)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)


    return render(request, 'orders/my_orders.html', {"users": users, 'page_obj': page_obj,
                                                     "data_orders": dataOrders, "active_page":"my_orders"})


def get_orders(request) -> HttpResponse:
    """
    Страница с JSON данными всех заказов
    """

    if 'HTTP_AUTHORIZATION' in request.META:

        # Получаем данные о Basiс AUTHORIZATION
        auth = request.META['HTTP_AUTHORIZATION'].split()
        if len(auth) == 2:
            if auth[0].lower() == "basic":

                # Получаем зашифрованную строку с логином и паролем и декодируем в строку
                data_auth: str = base64.b64decode(auth[1]).decode()
                # Разбиваем на логин и пароль
                uname, passwd = data_auth.split(':')
                # Пробуем авторизоваться
                user = authenticate(username=uname, password=passwd)

                if user is not None and user.is_active:
                    # Авторизация прошла успешно

                    # Получение всех заказов
                    orders: Order = Order.objects.all()

                    # Приведение списка заказов к json
                    orders_serialized = serializers.serialize('json', orders)

                    return JsonResponse({"orders": orders_serialized}, safe=False)

    response = HttpResponse()
    response.status_code = 401
    response['WWW-Authenticate'] = 'Basic realm="%s"' % "Basci Auth Protected"
    return response