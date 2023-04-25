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
            'Привет! Я могу показать город или сказать расстояние между городами!'
        return
    # Получаем города из нашего
    cities = get_cities(req)
    if not cities:
        res['response']['text'] = 'Ты не написал название не одного города!'
    elif len(cities) == 1:
        res['response']['text'] = 'Этот город в стране - ' + \
                                  get_country(cities[0])
    elif len(cities) == 2:
        distance = get_distance(get_coordinates(
            cities[0]), get_coordinates(cities[1]))
        res['response']['text'] = 'Расстояние между этими городами: ' + \
                                  str(round(distance)) + ' км.'
    else:
        res['response']['text'] = 'Слишком много городов!'


def get_cities(req):
    cities = []
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.GEO':
            if 'city' in entity['value']:
                cities.append(entity['value']['city'])
    return cities


if __name__ == '__main__':
    app.run()
