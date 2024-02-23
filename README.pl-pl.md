<div align="center">
   <h1>Telegram Bot</h1>
   <h3>🤖</h3>
   <h3>Wielofunkcyjny Bot na platformie Telegram</h3>
   <a href="https://t.me/Cezary924Bot" target="__blank"><img alt="Etykieta z napisem 'Telegram Bot' - link prowadzi do czatu z Cezary924Bot na platformie Telegram" src="https://img.shields.io/badge/Telegram-Bot-222222?style=for-the-badge&logo=telegram&logoColor=30A3E6"></a><br/><br/>
   <a href="https://github.com/Cezary924/Telegram-Bot/blob/master/README.md" target="__blank"><img alt="A Etykieta z napisem 'Jęz 🇬🇧' - link prowadzi do pliku README w języku angielskim" src="https://img.shields.io/badge/Jęz-🇬🇧-012169?style=for-the-badge"></a>
   <a href="https://github.com/Cezary924/Telegram-Bot/blob/master/README.pl-pl.md" target="__blank"><img alt="A Etykieta z napisem 'Jęz 🇵🇱' - link prowadzi do pliku README w języku polskim" src="https://img.shields.io/badge/Jęz-🇵🇱-dc143c?style=for-the-badge"></a>
</div><br/>

## ✨ Główne funkcje
- Pobieranie wideo z popularnych serwisów ⬇️ (TikTok, Twitter (X), Tumblr, Reddit, YouTube & Instagram)
- Przypomnienia 🔔
- Konwerter jednostek miar 🧮
- Zgadywanie jednego z topowych artystów serwisu Spotify ᯤ
- Magiczna kryształowa kula 🔮
- Wielojęzyczne odpowiedzi 🌐 (Polski & Angielski)
- Zarządzanie użytkownikami 🙋‍♂️🙋‍♀️ (Zmiana ról & Usuwanie danych)
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
   bot_name: nazwa_bota
   github_repo: nazwa_repo_github
   github_username: nazwa_uzytkownika_github
   telegram_username: nazwa_uzytkownika_telegram
   ```
   - plik ```tokens.yaml``` w folderze *files* i wprowadź do niego poniższy kod:
   ```
   telegram: token_telegram
   telegram_beta: inny_token_telegram
   rapidapi: rapidapi_token
   spotify_id: spotify_client_id
   spotify_secret: spotify_client_secret
   ```
   > RapidApi dla multimediów z serwisu TikTok: należy zasubskrybować https://rapidapi.com/maatootz/api/tiktok-full-info-without-watermark
   > RapidApi dla multimediów z serwisu Twitter (X): należy zasubskrybować https://rapidapi.com/JustMobi/api/twitter-downloader-download-twitter-videos-gifs-and-images
   > Tokeny Spotify: należy utworzyć aplikację w serwisie Spotify dla deweloperów https://developer.spotify.com/dashboard

## 🚀 Start
1. Aby uruchomić Bota, wykonaj to polecenie będąc w głównym folderze:
```
python bot/bot.py
```
> Możesz również dodać argument wywołania ```beta``` na końcu powyższej komendy, aby skorzystać z drugiego Telegram tokenu.
2. Gotowe!

## 🧑‍💻 Podstawowe komendy
- ```/start``` - Zaczęcie rozmowy z Botem.
- ```/features``` - Sprawdzenie listy wszystkich funkcji Bota.
- ```/help``` - Wyświetlenie menu pomocy z listą dostępnych komend.
- ```/about``` - Informacje o Bocie.
- ```/settings``` - Wyświetlenie menu ustawień z listą dostępnych opcji.
- ```/admin``` - _(ukryta komenda)_ Wyświetlenie menu Administratora.
- ```/reminder``` - Przypominanie o zadanych zdarzeniach.
- ```/unitconverter``` - Zamiana podstawowych jednostek miar.
- ```/tiktok``` - Pobieranie wideo z serwisu TikTok.
- ```/twitter``` - Pobieranie wideo z serwisu Twitter (X).
- ```/tumblr``` - Pobieranie wideo z serwisu Tumblr.
- ```/reddit``` - Pobieranie wideo z serwisu Reddit.
- ```/youtube``` - Pobieranie wideo z serwisu YouTube.
- ```/instagram``` - Pobieranie wideo z serwisu Instagram.
- ```/crystalball``` - Odpowiedź na Twoje pytanie.
- ```/topspotifyartist``` - Zgadywanie pseudonimu jednego z najpopularniejszych artystów serwisu Spotify.
- ```/contact``` - Informacje o drogach kontaktu z Administratorem.
- ```/report``` - Wysłanie zgłoszenia do Administratora.
