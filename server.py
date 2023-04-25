from flask import Flask, request, jsonify
import logging
import math
import requests


def get_coordinates(city_name):
    try:
        # url, по которому доступно API Яндекс.Карт
        url = "https://geocode-maps.yandex.ru/1.x/"
        # параметры запроса
        params = {
            "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
            # город, координаты которого мы ищем
            'geocode': city_name,
            # формат ответа от сервера, в данном случае JSON
            'format': 'json'
        }
        # отправляем запрос
        response = requests.get(url, params)
        # получаем JSON ответа
        json = response.json()
        # получаем координаты города
        # (там написаны долгота(longitude), широта(latitude) через пробел)
        # посмотреть подробное описание JSON-ответа можно
        # в документации по адресу https://tech.yandex.ru/maps/geocoder/
        coordinates_str = json['response']['GeoObjectCollection'][
            'featureMember'][0]['GeoObject']['Point']['pos']
        # Превращаем string в список, так как
        # точка - это пара двух чисел - координат
        long, lat = map(float, coordinates_str.split())
        # Вернем ответ
        return long, lat
    except Exception as e:
        return e


def get_country(city_name):
    try:
        url = "https://geocode-maps.yandex.ru/1.x/"
        params = {
            "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
            'geocode': city_name,
            'format': 'json'
        }
        data = requests.get(url, params).json()
        # все отличие тут, мы получаем имя страны
        return data['response']['GeoObjectCollection'][
            'featureMember'][0]['GeoObject']['metaDataProperty'][
            'GeocoderMetaData']['AddressDetails']['Country']['CountryName']
    except Exception as e:
        return e


def get_geo_info(city_name: str, type_info: str):
    if type_info == 'country':
        return get_country(city_name)
    return get_coordinates(city_name)


def get_distance(p1, p2):
    # p1 и p2 - это кортежи из двух элементов - координаты точек
    radius = 6373.0

    lon1 = math.radians(p1[0])
    lat1 = math.radians(p1[1])
    lon2 = math.radians(p2[0])
    lat2 = math.radians(p2[1])

    d_lon = lon2 - lon1
    d_lat = lat2 - lat1

    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * \
        math.cos(lat2) * math.sin(d_lon / 2) ** 2
    c = 2 * math.atan2(a ** 0.5, (1 - a) ** 0.5)

    distance = radius * c
    return distance


# импортируем функции из нашего второго файла geo

app = Flask(__name__)

# Добавляем логирование в файл.
# Чтобы найти файл, перейдите на pythonwhere в раздел files,
# он лежит в корневой папке
logging.basicConfig(level=logging.INFO, filename='app.log',
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')

sessionStorage = dict()


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)
    logging.info('Request: %r', response)
    return jsonify(response)


def handle_dialog(res, req):
    user_id = req['session']['user_id']
    if req['session']['new']:
        res['response']['text'] = \
            'Привет! Я могу показать город или сказать расстояние между городами!\nНазови своё имя'
        sessionStorage[user_id] = {'name': None}
        return
    if sessionStorage[user_id]['name'] == None:
        first_name = get_first_name(req)
        if first_name is None:
            res['response']['text'] = 'Не расслышала имя. Повтори, пожалуйста!'
            return
        else:
            sessionStorage[user_id]['name'] = first_name.capitalize()
            res['response']['text'] = f'{first_name.capitalize()}, введи название одного или двух городов'
            return
        # Получаем города из нашего
    cities = get_cities(req)
    name = sessionStorage[user_id]['name']
    if not cities:
        res['response']['text'] = f'{name}, ты не написал название не одного города!'
    elif len(cities) == 1:
        res['response']['text'] = f'{name}, этот город в стране - ' + \
                                  get_geo_info(cities[0], 'country')
    elif len(cities) == 2:
        distance = get_distance(get_geo_info(
            cities[0], 'coordinates'), get_geo_info(cities[1], 'coordinates'))
        res['response']['text'] = f'{name}, расстояние между этими городами: ' + \
                                  str(round(distance)) + ' км.'
    else:
        res['response']['text'] = f'{name}, слишком много городов!'


def get_cities(req):
    cities = []
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.GEO':
            if 'city' in entity['value']:
                cities.append(entity['value']['city'])
    return cities


def get_first_name(req):
    # перебираем сущности
    for entity in req['request']['nlu']['entities']:
        # находим сущность с типом 'YANDEX.FIO'
        if entity['type'] == 'YANDEX.FIO':
            # Если есть сущность с ключом 'first_name', то возвращаем её значение.
            # Во всех остальных случаях возвращаем None.
            return entity['value'].get('first_name', None)


if __name__ == '__main__':
    app.run()
