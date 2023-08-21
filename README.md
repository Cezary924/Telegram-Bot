<div align="center">
   <h1>Cezary924-Telegram-Bot</h1>
   <h3>🤖</h3>
   <h3>Multifunctional Telegram Bot</h3>
   <a href="https://t.me/Cezary924Bot" target="__blank"><img src="https://img.shields.io/badge/Telegram-Bot-blue.svg?logo=telegram"></a><br/><br/>
   <a href="https://github.com/Cezary924/Cezary924-Telegram-Bot/blob/master/README.md" target="__blank"><img src="https://img.shields.io/badge/lang-en-blue.svg"></a>
   <a href="https://github.com/Cezary924/Cezary924-Telegram-Bot/blob/master/README.pl-pl.md" target="__blank"><img src="https://img.shields.io/badge/lang-pl-red.svg"></a>
</div><br/>

## ✨ Main features
- Video downloader ⬇️ (TikTok, Twitter, Tumblr, Reddit, YouTube & Instagram)
   > Due to a name change to X, Twitter video downloader is currently unavailable.
- Guess Top Spotify Artist ᯤ
- Crystal ball 🔮
- Multilingual responses 🌐 (English & Polish)
- Device status management ⚙️ (Shutdown & Restart) 

## ⚙️ Installation & Configuration
1. Clone this repo.
2. Install required libraries with this code:
```
pip install -r requirements.txt
```
3. Create:
   - ```config.yaml``` file in *files* folder and write following code to it:
   ```
   bot_name: your_bot_name
   github_repo: your_github_repo_name
   github_username: your_github_username
   telegram_username: your_telegram_username
   ```
   - ```tokens.yaml``` file in *files* folder and write following code to it:
   ```
   telegram: your_telegram_token
   telegram_beta: your_another_telegram_token
   tiktok: your_rapidapi_token
   twitter: your_another_rapidapi_token
   spotify_id: your_spotify_client_id
   spotify_secret: your_spotify_client_secret
   ```
   > RapidApi for TikTok media: https://rapidapi.com/maatootz/api/tiktok-full-info-without-watermark
   > RapidApi for Twitter media: https://rapidapi.com/3205/api/twitter65
   > Spotify Tokens: you have to create an app in the Spotify Developer Dashboard https://developer.spotify.com/dashboard

## 🚀 Starting
1. To start, execute this command in the main directory:
```
python bot/bot.py
```
> You can also use ```beta``` argument to use secondary Telegram token.
```
python bot/bot.py beta
```
2. Enjoy!

## 🧑‍💻 Basic commands
- ```/start``` - to start conversation with the Bot.
- ```/help``` - to get info about available commands.
- ```/about``` - to get info about the Bot and its Creator.
- ```/admin``` - _(hidden command)_ to get access to the Admin Menu.
- ```/tiktok``` - to download video from TikTok.
- ```/twitter``` - to download video from Twitter.
- ```/tumblr``` - to download video from Tumblr.
- ```/reddit``` - to download video from Reddit.
- ```/youtube``` - to download video from YouTube.
- ```/instagram``` - to download video from Instagram.
- ```/topspotifyartist``` - to guess one of the top Spotify artists.
- ```/crystalball``` - to answer your question.
- ```/contact``` - to contact the Admin/Creator.
- ```/report``` - to report an issue to the Admin.
- ```/language``` - to change your display language.
- ```/deletedata``` - to delete all your data collected by the Bot.
