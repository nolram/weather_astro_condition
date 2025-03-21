import os
import requests
from dotenv import load_dotenv
from datetime import datetime

# Carrega as variáveis do arquivo .env
load_dotenv()


def get_weather(lat, lon, api_key):
    """
    Consulta a API One Call da OpenWeatherMap para obter os dados meteorológicos.
    """
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
    """
    Avalia as condições gerais para observação com base em dados atuais e previsão diária:
      - Cobertura de nuvens;
      - Precipitação (chuva/neve na última hora);
      - Umidade relativa;
      - Velocidade do vento;
      - Probabilidade de precipitação (pop);
      - Fase da Lua.
    """
    results = {}
    current = weather_data.get("current", {})

    # Cobertura de nuvens
    clouds = current.get("clouds", 100)
    results["clouds"] = clouds
    results["clouds_good"] = clouds < thresholds["clouds"]

    # Precipitação atual (chuva/neve na última hora)
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

    # Avaliação geral
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
    """
    Analisa as condições durante o período noturno (20h às 6h) usando a previsão horária.
    Retorna um dicionário com os piores (maiores) valores dos parâmetros relevantes.
    """
    results = {}
    hourly = weather_data.get("hourly", [])
    timezone_offset = weather_data.get("timezone_offset", 0)  # Offset em segundos

    # Filtra os dados para o período noturno (20h às 6h, horário local)
    night_hours = []
    for hour in hourly:
        local_time = datetime.fromtimestamp(hour["dt"] + timezone_offset)
        if local_time.hour >= 20 or local_time.hour < 6:
            night_hours.append(hour)

    if not night_hours:
        return None

    # Obtém os piores valores durante o período noturno
    max_clouds = max(hour.get("clouds", 0) for hour in night_hours)
    max_precip = 0
    for hour in night_hours:
        # Pode existir a chave "rain" ou "snow" em diferentes formatos
        rain = 0
        if "rain" in hour:
            if isinstance(hour["rain"], dict):
                rain = hour["rain"].get("1h", 0)
            else:
                rain = hour.get("rain", 0)
        snow = 0
        if "snow" in hour:
            if isinstance(hour["snow"], dict):
                snow = hour["snow"].get("1h", 0)
            else:
                snow = hour.get("snow", 0)
        precip = rain + snow
        if precip > max_precip:
            max_precip = precip

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

    # Avaliação geral noturna (a fase da Lua não é considerada aqui, pois é um valor diário)
    overall = (
        results["clouds_good"]
        and results["precipitation_good"]
        and results["humidity_good"]
        and results["wind_good"]
        and results["pop_good"]
    )
    results["overall_good"] = overall

    return results


def main():
    # Obter variáveis de ambiente do arquivo .env
    api_key = os.environ.get("OPENWEATHERMAP_API_KEY")
    if not api_key:
        raise ValueError("A variável OPENWEATHERMAP_API_KEY não foi definida no .env.")

    try:
        lat = float(os.environ.get("LATITUDE"))
        lon = float(os.environ.get("LONGITUDE"))
    except (TypeError, ValueError):
        raise ValueError(
            "As variáveis LATITUDE e LONGITUDE devem estar definidas no .env com valores numéricos."
        )

    # Definição dos thresholds (limiares) para cada parâmetro:
    thresholds = {
        "clouds": 20,  # porcentagem máxima de nuvens permitida
        "humidity": 80,  # umidade relativa máxima (%)
        "wind_speed": 5,  # velocidade do vento máxima (m/s)
        "pop": 0.2,  # probabilidade máxima de precipitação (20%)
        "moon_low": 0.25,  # valores abaixo de 0.25 indicam lua nova (ideal)
        "moon_high": 0.75,  # valores acima de 0.75 também indicam proximidade com lua nova
    }

    weather_data = get_weather(lat, lon, api_key)
    if weather_data:
        daily_results = is_good_for_observation(weather_data, thresholds)
        night_results = analyze_night_conditions(weather_data, thresholds)

        print("Condições gerais para observação:")
        print(
            f"  Cobertura de nuvens: {daily_results['clouds']}% -> {'Bom' if daily_results['clouds_good'] else 'Ruim'}"
        )
        print(
            f"  Precipitação (última hora): {daily_results['precipitation']} mm -> {'Bom' if daily_results['precipitation_good'] else 'Ruim'}"
        )
        print(
            f"  Umidade: {daily_results['humidity']}% -> {'Bom' if daily_results['humidity_good'] else 'Ruim'}"
        )
        print(
            f"  Velocidade do vento: {daily_results['wind_speed']} m/s -> {'Bom' if daily_results['wind_good'] else 'Ruim'}"
        )
        print(
            f"  Probabilidade de precipitação (pop): {daily_results.get('pop', 'N/A')} -> {'Bom' if daily_results.get('pop_good') else 'Ruim'}"
        )
        print(
            f"  Fase da Lua: {daily_results.get('moon_phase', 'N/A')} -> {'Bom' if daily_results.get('moon_good') else 'Ruim'}"
        )
        print(
            "Condições gerais:",
            "Favoráveis" if daily_results["overall_good"] else "Não favoráveis",
        )

        if night_results:
            print("\nCondições noturnas (20h às 6h):")
            print(
                f"  Cobertura de nuvens: {night_results['clouds']}% -> {'Bom' if night_results['clouds_good'] else 'Ruim'}"
            )
            print(
                f"  Precipitação: {night_results['precipitation']} mm -> {'Bom' if night_results['precipitation_good'] else 'Ruim'}"
            )
            print(
                f"  Umidade: {night_results['humidity']}% -> {'Bom' if night_results['humidity_good'] else 'Ruim'}"
            )
            print(
                f"  Velocidade do vento: {night_results['wind_speed']} m/s -> {'Bom' if night_results['wind_good'] else 'Ruim'}"
            )
            print(
                f"  Probabilidade de precipitação (pop): {night_results.get('pop', 'N/A')} -> {'Bom' if night_results.get('pop_good') else 'Ruim'}"
            )
            print(
                "Condições noturnas:",
                "Favoráveis" if night_results["overall_good"] else "Não favoráveis",
            )
        else:
            print("Não há dados suficientes para análise noturna.")
    else:
        print("Não foi possível obter os dados meteorológicos.")


if __name__ == "__main__":
    main()
