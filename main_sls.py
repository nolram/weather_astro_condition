import os
import requests
import boto3
from dotenv import load_dotenv
from datetime import datetime

# Carrega variáveis do .env (útil para desenvolvimento local)
load_dotenv()


def get_weather(lat, lon, api_key):
    url = (
        f"https://api.openweathermap.org/data/3.0/onecall?"
        f"lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
    )
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print("Erro ao obter dados:", response.status_code)
        return None


def is_good_for_observation(weather_data, thresholds):
    results = {}
    current = weather_data.get("current", {})

    # Cobertura de nuvens
    clouds = current.get("clouds", 100)
    results["clouds"] = clouds
    results["clouds_good"] = clouds < thresholds["clouds"]

    # Precipitação (chuva/neve na última hora)
    rain = current.get("rain", {}).get("1h", 0)
    snow = current.get("snow", {}).get("1h", 0)
    precipitation = rain + snow
    results["precipitation"] = precipitation
    results["precipitation_good"] = precipitation == 0

    # Umidade
    humidity = current.get("humidity", 100)
    results["humidity"] = humidity
    results["humidity_good"] = humidity < thresholds["humidity"]

    # Velocidade do vento
    wind_speed = current.get("wind_speed", 0)
    results["wind_speed"] = wind_speed
    results["wind_good"] = wind_speed < thresholds["wind_speed"]

    # Previsão diária (primeiro dia)
    daily = weather_data.get("daily", [])
    if daily:
        today = daily[0]
        pop = today.get("pop", 0)
        results["pop"] = pop
        results["pop_good"] = pop < thresholds["pop"]

        moon_phase = today.get("moon_phase", 0)
        results["moon_phase"] = moon_phase
        results["moon_good"] = (
            moon_phase < thresholds["moon_low"] or moon_phase > thresholds["moon_high"]
        )
    else:
        results["pop"] = None
        results["pop_good"] = False
        results["moon_phase"] = None
        results["moon_good"] = False

    overall = (
        results["clouds_good"]
        and results["precipitation_good"]
        and results["humidity_good"]
        and results["wind_good"]
        and results["pop_good"]
        and results["moon_good"]
    )
    results["overall_good"] = overall

    return results


def analyze_night_conditions(weather_data, thresholds):
    results = {}
    hourly = weather_data.get("hourly", [])
    timezone_offset = weather_data.get("timezone_offset", 0)  # em segundos

    # Filtra para o período noturno (20h às 6h, horário local)
    night_hours = []
    for hour in hourly:
        local_time = datetime.fromtimestamp(hour["dt"] + timezone_offset)
        if local_time.hour >= 20 or local_time.hour < 6:
            night_hours.append(hour)

    if not night_hours:
        return None

    max_clouds = max(hour.get("clouds", 0) for hour in night_hours)
    max_precip = 0
    for hour in night_hours:
        rain = (
            hour.get("rain", {}).get("1h", 0)
            if isinstance(hour.get("rain"), dict)
            else hour.get("rain", 0)
        )
        snow = (
            hour.get("snow", {}).get("1h", 0)
            if isinstance(hour.get("snow"), dict)
            else hour.get("snow", 0)
        )
        precip = rain + snow
        max_precip = max(max_precip, precip)

    max_humidity = max(hour.get("humidity", 0) for hour in night_hours)
    max_wind = max(hour.get("wind_speed", 0) for hour in night_hours)
    max_pop = max(hour.get("pop", 0) for hour in night_hours)

    results["clouds"] = max_clouds
    results["precipitation"] = max_precip
    results["humidity"] = max_humidity
    results["wind_speed"] = max_wind
    results["pop"] = max_pop

    results["clouds_good"] = max_clouds < thresholds["clouds"]
    results["precipitation_good"] = max_precip == 0
    results["humidity_good"] = max_humidity < thresholds["humidity"]
    results["wind_good"] = max_wind < thresholds["wind_speed"]
    results["pop_good"] = max_pop < thresholds["pop"]

    overall = (
        results["clouds_good"]
        and results["precipitation_good"]
        and results["humidity_good"]
        and results["wind_good"]
        and results["pop_good"]
    )
    results["overall_good"] = overall

    return results


def send_email(subject, body):
    ses = boto3.client("ses", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    response = ses.send_email(
        Source=os.environ.get("SES_FROM_EMAIL"),
        Destination={"ToAddresses": [os.environ.get("SES_TO_EMAIL")]},
        Message={"Subject": {"Data": subject}, "Body": {"Text": {"Data": body}}},
    )
    return response


def lambda_handler(event, context):
    # Obter variáveis de ambiente
    api_key = os.environ.get("OPENWEATHERMAP_API_KEY")
    try:
        lat = float(os.environ.get("LATITUDE"))
        lon = float(os.environ.get("LONGITUDE"))
    except (TypeError, ValueError):
        raise ValueError(
            "As variáveis LATITUDE e LONGITUDE devem ser definidas com valores numéricos."
        )

    thresholds = {
        "clouds": 20,  # % máximo de nuvens
        "humidity": 80,  # umidade máxima (%)
        "wind_speed": 5,  # vento máximo (m/s)
        "pop": 0.2,  # probabilidade máxima de precipitação (20%)
        "moon_low": 0.25,  # valores abaixo indicam lua nova (ideal)
        "moon_high": 0.75,  # valores acima indicam proximidade com lua nova
    }

    weather_data = get_weather(lat, lon, api_key)
    if weather_data:
        daily_results = is_good_for_observation(weather_data, thresholds)
        night_results = analyze_night_conditions(weather_data, thresholds)

        # Monta o corpo do e-mail
        email_body = "Status Diário para Observação Astronômica:\n\n"
        email_body += "Condições Gerais:\n"
        email_body += f"  Cobertura de nuvens: {daily_results['clouds']}% -> {'Bom' if daily_results['clouds_good'] else 'Ruim'}\n"
        email_body += f"  Precipitação: {daily_results['precipitation']} mm -> {'Bom' if daily_results['precipitation_good'] else 'Ruim'}\n"
        email_body += f"  Umidade: {daily_results['humidity']}% -> {'Bom' if daily_results['humidity_good'] else 'Ruim'}\n"
        email_body += f"  Velocidade do vento: {daily_results['wind_speed']} m/s -> {'Bom' if daily_results['wind_good'] else 'Ruim'}\n"
        email_body += f"  Probabilidade de chuva (pop): {daily_results.get('pop', 'N/A')} -> {'Bom' if daily_results.get('pop_good') else 'Ruim'}\n"
        email_body += f"  Fase da Lua: {daily_results.get('moon_phase', 'N/A')} -> {'Bom' if daily_results.get('moon_good') else 'Ruim'}\n"
        email_body += f"\nCondições Gerais: {'Favoráveis' if daily_results['overall_good'] else 'Não favoráveis'}\n\n"

        if night_results:
            email_body += "Condições Noturnas (20h às 6h):\n"
            email_body += f"  Cobertura de nuvens: {night_results['clouds']}% -> {'Bom' if night_results['clouds_good'] else 'Ruim'}\n"
            email_body += f"  Precipitação: {night_results['precipitation']} mm -> {'Bom' if night_results['precipitation_good'] else 'Ruim'}\n"
            email_body += f"  Umidade: {night_results['humidity']}% -> {'Bom' if night_results['humidity_good'] else 'Ruim'}\n"
            email_body += f"  Velocidade do vento: {night_results['wind_speed']} m/s -> {'Bom' if night_results['wind_good'] else 'Ruim'}\n"
            email_body += f"  Probabilidade de chuva (pop): {night_results.get('pop', 'N/A')} -> {'Bom' if night_results.get('pop_good') else 'Ruim'}\n"
            email_body += f"\nCondições Noturnas: {'Favoráveis' if night_results['overall_good'] else 'Não favoráveis'}\n"
        else:
            email_body += "\nNão há dados suficientes para análise noturna.\n"

        subject = "Status Diário: Observação Astronômica"
        send_email(subject, email_body)
        print("E-mail enviado com sucesso!")
    else:
        error_msg = "Erro: Não foi possível obter os dados meteorológicos."
        send_email("Erro no Serviço de Observação Astronômica", error_msg)
        print("Falha ao obter dados meteorológicos.")


# Para testes locais
if __name__ == "__main__":
    lambda_handler({}, None)
