# Analisador de Condições para Observação Astronômica

Este projeto utiliza a API One Call do OpenWeatherMap para obter dados meteorológicos e avaliar se as condições estão favoráveis para observações astronômicas. Ele analisa parâmetros como cobertura de nuvens, precipitação, umidade, velocidade do vento, probabilidade de precipitação (pop) e fase da Lua, além de realizar uma análise específica para o período noturno (das 20h às 6h, horário local).

## Funcionalidades

- **Coleta de Dados:** Recupera informações meteorológicas atuais, horárias e diárias da API do OpenWeatherMap.
- **Avaliação Geral:** Analisa os dados atuais e diários para determinar se as condições são propícias para observação.
- **Análise Noturna:** Filtra os dados da previsão horária para o período noturno e extrai os piores valores dos parâmetros relevantes.
- **Configuração via .env:** Utiliza a biblioteca `python-dotenv` para carregar as credenciais e as coordenadas geográficas a partir de um arquivo `.env`.

## Requisitos

- Python 3.x
- Bibliotecas Python:
  - `requests`
  - `python-dotenv`

## Instalação

1. **Clone o repositório** (ou copie os arquivos para sua máquina).

2. **Instale as dependências** executando:

```bash
pipenv install
```

3. **Crie o arquivo .env**

```bash
cp .env.example .env
```

4. **Preencha os dados do .env**

```env
OPENWEATHERMAP_API_KEY=SuaChaveDaAPI
LATITUDE=-23.550520
LONGITUDE=-46.633308
```

Obtenha a chave do `OPENWEATHERMAP_API_KEY` no site [https://home.openweathermap.org/api_keys](https://home.openweathermap.org/api_keys)
E substitua a `LATITUDE` e `LONGITUDE` da região que você deseja analisar.

5. **Execute o script**

```bash
python main.py
Condições gerais para observação:
  Cobertura de nuvens: 20% -> Ruim
  Precipitação (última hora): 0 mm -> Bom
  Umidade: 43% -> Bom
  Velocidade do vento: 3.6 m/s -> Bom
  Probabilidade de precipitação (pop): 0 -> Bom
  Fase da Lua: 0.72 -> Ruim
Condições gerais: Não favoráveis

Condições noturnas (20h às 6h):
  Cobertura de nuvens: 100% -> Ruim
  Precipitação: 0 mm -> Bom
  Umidade: 88% -> Ruim
  Velocidade do vento: 4.63 m/s -> Bom
  Probabilidade de precipitação (pop): 0 -> Bom
Condições noturnas: Não favoráveis
```
