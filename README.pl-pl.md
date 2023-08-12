<div align="center">
   <h1>Cezary924-Telegram-Bot</h1>
   <h3>🤖</h3>
   <h3>Wielofunkcyjny Bot na platformie Telegram</h3>
   <a href="https://t.me/Cezary924Bot" target="__blank"><img src="https://img.shields.io/badge/Telegram-Bot-blue.svg?logo=telegram"></a><br/><br/>
   <a href="https://github.com/Cezary924/Cezary924-Telegram-Bot/blob/master/README.md" target="__blank"><img src="https://img.shields.io/badge/lang-en-blue.svg"></a>
   <a href="https://github.com/Cezary924/Cezary924-Telegram-Bot/blob/master/README.pl-pl.md" target="__blank"><img src="https://img.shields.io/badge/lang-pl-red.svg"></a>
</div><br/>

## ✨ Główne funkcje
- Pobieranie wideo z popularnych serwisów (TikTok, Twitter, Tumblr, Reddit & YouTube)
- Zgadywanie jednego z topowych artystów serwisu Spotify ᯤ
- Magiczna kryształowa kula 🔮
- Wielojęzyczne odpowiedzi 🌐 (Angielski & Polski)
- Zarządzanie stanem urządzenia ⚙️ (Wyłączanie & Ponowne uruchamianie) 

## ⚙️ Instalacja i konfiguracja
1. Sklonuj to repozytorium.
2. Zainstaluj wymagane biblioteki przy pomocy tego polecenia:
```
pip install -r requirements.txt
```
3. Stwórz:
   - plik ```config.yaml``` w folderze *files* i wprowadź do niego poniższy kod:
   ```
   bot_name: yourbotname
   github_repo: yourgithubrepo
   github_username: yourgithubusername
   telegram_username: yourtelegramusername
   ```
   - plik ```tokens.yaml``` w folderze *files* i wprowadź do niego poniższy kod:
   ```
   telegram: yourtelegramtoken
   telegram_beta: youranothertelegramtoken
   tiktok: yourrapidapitoken
   twitter: youranotherrapidapitoken
   spotify_id: yourspotifyclientid
   spotify_secret: yourspotifyclientsecret
   ```
   > RapidApi dla multimediów z serwisu TikTok: https://rapidapi.com/maatootz/api/tiktok-full-info-without-watermark
   > RapidApi dla multimediów z serwisu Twitter: https://rapidapi.com/3205/api/twitter65
   > Tokeny Spotify: należy utworzyć aplikację w serwisie Spotify dla deweloperów https://developer.spotify.com/dashboard

## 🚀 Start
1. Aby uruchomić Bota, wykonaj to polecenie będąc w głównym folderze:
```
python bot/bot.py
```
> Możesz również użyc argumentu wywołania ```beta```, aby skorzystać z drugiego Telegram tokenu.
```
python bot/bot.py beta
```
2. Gotowe! 😁

## 🧑‍💻 Podstawowe komendy
- ```/start``` - Zaczęcie rozmowy z Botem.
- ```/help``` - Wyświetlenie menu pomocy z listą dostępnych komend.
- ```/about``` - Informacje o Bocie.
- ```/admin``` - _(ukryta komenda)_ Wyświetlenie menu Administratora.
- ```/tiktok``` - Pobieranie wideo z serwisu TikTok.
- ```/twitter``` - Pobieranie wideo z serwisu Twitter.
- ```/tumblr``` - Pobieranie wideo z serwisu Tumblr.
- ```/reddit``` - Pobieranie wideo z serwisu Reddit.
- ```/topspotifyartist``` - Zgadywanie pseudonimu jednego z najpopularniejszych artystów serwisu Spotify
- ```/crystalball``` - Odpowiedź na Twoje pytanie.
- ```/contact``` - Informacje o drogach kontaktu z Administratorem.
- ```/report``` - Wysłanie zgłoszenia do Administratora.
- ```/language``` - Zmiana języka.
- ```/deletedata``` - Usunięcie wszystkich zgromadzonych danych.
