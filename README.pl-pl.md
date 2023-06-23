<div align="center">
   <h1>Cezary924-Telegram-Bot</h1>
   <h3>🤖</h3>
   <h3>Wielofunkcyjny Bot na platformie Telegram</h3>
   <a href="https://t.me/Cezary924Bot" target="__blank"><img src="https://img.shields.io/badge/Telegram-Bot-blue.svg?logo=telegram"></a><br/><br/>
   <a href="https://github.com/Cezary924/Cezary924-Telegram-Bot/blob/master/README.md" target="__blank"><img src="https://img.shields.io/badge/lang-en-blue.svg"></a>
   <a href="https://github.com/Cezary924/Cezary924-Telegram-Bot/blob/master/README.pl-pl.md" target="__blank"><img src="https://img.shields.io/badge/lang-pl-red.svg"></a>
</div><br/>

## ✨ Główne funkcje
- Pobieranie wideo z popularnych serwisów (TikTok, Twitter, Tumblr & Reddit)

## ⚙️ Instalacja i konfiguracja
1. Sklonuj to repozytorium.
2. Zainstaluj wymagane biblioteki przy pomocy tego polecenia:
```
pip install -r requirements.txt
```
3. Stwórz:
   - plik ```telegram.txt``` w folderze *files* i zapisz w nim swój Telegram token.
   - plik ```tiktok.txt``` w folderze *files* i zapisz w nim swój RapidAPI key (https://rapidapi.com/maatootz/api/tiktok-full-info-without-watermark).
   - plik ```twitter.txt``` w folderze *files* i zapisz w nim swój (inny) RapidAPI key (https://rapidapi.com/3205/api/twitter65).
4. Zmień:
   - plik ```bot_name.txt``` z folderu *files* - wprowadź swoją własną nazwę Bota.
   - plik ```github_username.txt``` z folderu *files* - wprowadź swoją nazwę uzytkownika GitHub.
   - plik ```github_repo.txt``` z folderu *files* - wprowadź nazwę swojego repozytorium GitHub.

## 🚀 Start
1. Aby uruchomić Bota, wykonaj to polecenie będąc w głównym folderze:
```
python bot/bot.py
```
2. Gotowe! Korzystaj i ciesz się! 😁

## 🧑‍💻 Podstawowe komendy
- ```/start``` - Zaczęcie rozmowy z Botem.
- ```/help``` - Wyświetlenie menu pomocy z listą dostępnych komend.
- ```/about``` - Informacje o Bocie.
- ```/admin``` - _(ukryta komenda)_ Wyświetlenie menu Administratora.
- ```/tiktok``` - Pobieranie wideo z serwisu TikTok.
- ```/twitter``` - Pobieranie wideo z serwisu Twitter.
- ```/tumblr``` - Pobieranie wideo z serwisu Tumblr.
- ```/reddit``` - Pobieranie wideo z serwisu Reddit.
- ```/contact``` - Informacje o drogach kontaktu z Administratorem.
- ```/report``` - Wysłanie zgłoszenia do Administratora.
- ```/language``` - Zmiana języka.
- ```/deletedata``` - Usunięcie wszystkich zgromadzonych danych.
