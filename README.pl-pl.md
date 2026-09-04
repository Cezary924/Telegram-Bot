<div align="center">
   <h1>Telegram Bot</h1>
   <h3>🤖</h3>
   <h3>Wielofunkcyjny Bot na platformie Telegram</h3>
   <a href="https://t.me/Cezary924Bot" target="__blank"><img alt="Etykieta z napisem 'Telegram Bot' - link prowadzi do czatu z Cezary924Bot na platformie Telegram" src="https://img.shields.io/badge/Telegram-Bot-222222?style=for-the-badge&logo=telegram&logoColor=30A3E6"></a>
   <a href="https://github.com/Cezary924/Telegram-Bot/actions/workflows/ci.yml" target="__blank"><img alt="Etykieta z napisem 'CI' - link prowadzi do przebiegów workflow na GitHubie" src="https://img.shields.io/github/actions/workflow/status/Cezary924/Telegram-Bot/ci.yml?style=for-the-badge&label=CI"></a><br/><br/>
   <a href="https://github.com/Cezary924/Telegram-Bot/blob/master/README.md" target="__blank"><img alt="Etykieta z napisem 'Jęz 🇬🇧' - link prowadzi do pliku README w języku angielskim" src="https://img.shields.io/badge/Jęz-🇬🇧-012169?style=for-the-badge"></a>
   <a href="https://github.com/Cezary924/Telegram-Bot/blob/master/README.pl-pl.md" target="__blank"><img alt="Etykieta z napisem 'Jęz 🇵🇱' - link prowadzi do pliku README w języku polskim" src="https://img.shields.io/badge/Jęz-🇵🇱-dc143c?style=for-the-badge"></a>
</div><br/>

## ⚙️ Instalacja i konfiguracja

1. Sklonuj to repozytorium.
2. Zainstaluj wymagane biblioteki przy pomocy tego polecenia:

```
pip install -r requirements.txt
```

3. Stwórz:
    - plik ```config.yaml``` w folderze *config* i wprowadź do niego poniższy kod:
   ```
   bot_name: nazwa_bota
   github_repo: nazwa_repo_github
   github_username: nazwa_uzytkownika_github
   telegram_username: nazwa_uzytkownika_telegram
   ```
    - plik ```tokens.yaml``` w folderze *config* i wprowadź do niego poniższy kod:
   ```
   telegram: token_telegram
   telegram_beta: inny_token_telegram
   spotify_id: spotify_client_id
   spotify_secret: spotify_client_secret
   ```
   > Tokeny Spotify: należy utworzyć aplikację w serwisie Spotify dla
   deweloperów https://developer.spotify.com/dashboard

4. Zainstaluj [ffmpeg](https://ffmpeg.org/download.html). Serwisy, które oddają obraz i dźwięk w osobnych plikach -
   a takim jest YouTube - bez niego się nie pobiorą.

## 🚀 Start

1. Aby uruchomić Bota, wykonaj to polecenie będąc w głównym folderze:

```
python src/bot.py
```

> Możesz również dodać argument wywołania ```beta``` na końcu powyższej komendy, aby skorzystać z drugiego Telegram
> tokenu.

2. Gotowe!

## 🧩 Moduły

Każda funkcja jest modułem - katalogiem, który Bot wczytuje przy starcie. Moduły funkcji da się wyłączyć w
```config/modules.yaml```, moduły rdzenia są zawsze na miejscu.
> Pisanie własnego modułu opisuje [MODULES.pl-pl.md](MODULES.pl-pl.md).

## 🧱 Moduły rdzenia

- Powitanie i lista funkcji 👋 (```/start```, ```/features```)
- Pomoc i informacje o Bocie 💬 (```/help```, ```/about```)
- Ustawienia, język i powiadomienia ⚙️ (```/settings```)
- Kontakt i zgłoszenia 📨 (```/contact```, ```/report```)
- Zarządzanie użytkownikami i Botem 🛠️ (```/admin```)

> ```/admin``` jest ukrytą komendą, dostępną wyłącznie dla Administratora.

## ✨ Moduły funkcjonalności dodatkowych

- Pobieranie wideo 📥 (```/downloader```)
- Przypomnienia 🔔 (```/reminder```)
- Konwerter jednostek miar 🧮 (```/unitconverter```)
- Zgadywanie topowego artysty Spotify ᯤ (```/topspotifyartist```)
- Magiczna kryształowa kula 🔮 (```/crystalball```)
