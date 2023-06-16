<h1 align=center>Cezary924-Telegram-Bot</h1>
<h3 align=center>🤖</h3>
<h3 align=center>Wielofunkcyjny Bot na platformie Telegram</h3>

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
   - plik ```tiktok.txt``` w folderze *files* i zapisz w nim swój RapidAPI key.
   - plik ```twitter.txt``` w folderze *files* i zapisz w nim swój Twitter bearer token.
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
- ```/deletedata``` - Usunięcie wszystkich zgromadzonych danych.
