<div align="center">
   <h1>Telegram Bot</h1>
   <h3>🤖</h3>
   <h3>Multifunctional Telegram Bot</h3>
   <a href="https://t.me/Cezary924Bot" target="__blank"><img alt="Badge with a label 'Telegram Bot' - a link takes to a chat with Cezary924Bot on Telegram" src="https://img.shields.io/badge/Telegram-Bot-222222?style=for-the-badge&logo=telegram&logoColor=30A3E6"></a><br/><br/>
   <a href="https://github.com/Cezary924/Telegram-Bot/blob/master/README.md" target="__blank"><img alt="A badge with a label 'Lang 🇬🇧' - a link takes to README file in English" src="https://img.shields.io/badge/Lang-🇬🇧-012169?style=for-the-badge"></a>
   <a href="https://github.com/Cezary924/Telegram-Bot/blob/master/README.pl-pl.md" target="__blank"><img alt="A badge with a label 'Lang 🇵🇱' - a link takes to README file in Polish" src="https://img.shields.io/badge/Lang-🇵🇱-dc143c?style=for-the-badge"></a>
</div><br/>

## ✨ Main features
- Video downloader ⬇️ (TikTok, Twitter (X), Tumblr, Reddit, YouTube & Instagram)
- Reminders 🔔
- Unit converter 🧮
- Guess Top Spotify Artist ᯤ
- Crystal ball 🔮
- Multilingual responses 🌐 (English & Polish)
- User management 🙋‍♀️🙋‍♂️ (Changing roles & Deleting data)
- Device status management ⚙️ (Shutdown & Restart) 

## ⚙️ Installation & Configuration
1. Clone this repo.
2. Install required libraries with this code:
```
pip install -r requirements.txt
```
3. Create:
   - ```config.yaml``` file in *config* folder and write following code to it:
   ```
   bot_name: your_bot_name
   github_repo: your_github_repo_name
   github_username: your_github_username
   telegram_username: your_telegram_username
   ```
   - ```tokens.yaml``` file in *config* folder and write following code to it:
   ```
   telegram: your_telegram_token
   telegram_beta: your_another_telegram_token
   rapidapi: your_rapidapi_token
   spotify_id: your_spotify_client_id
   spotify_secret: your_spotify_client_secret
   ```
   > RapidApi for TikTok media: you have to subscribe to https://rapidapi.com/maatootz/api/tiktok-full-info-without-watermark
   > RapidApi for Twitter (X) media: you have to subscribe to https://rapidapi.com/JustMobi/api/twitter-downloader-download-twitter-videos-gifs-and-images
   > Spotify Tokens: you have to create an app in the Spotify Developer Dashboard https://developer.spotify.com/dashboard

## 🚀 Starting
1. To start, execute this command in the main directory:
```
python src/bot.py
```
> You can also add ```beta``` argument at the end of the command shown above to use secondary Telegram token.
2. Enjoy!

## 🧑‍💻 Basic commands
- ```/start``` - to start conversation with the Bot.
- ```/features``` - to check all Bot features list.
- ```/help``` - to get info about available commands.
- ```/about``` - to get info about the Bot and its Creator.
- ```/settings``` - to get info about available settings.
- ```/admin``` - _(hidden command)_ to get access to the Admin Menu.
- ```/reminder``` - to be reminded of specific events.
- ```/unitconverter``` - To convert common units of measurement.
- ```/tiktok``` - to download video from TikTok.
- ```/twitter``` - to download video from Twitter (X).
- ```/tumblr``` - to download video from Tumblr.
- ```/reddit``` - to download video from Reddit.
- ```/youtube``` - to download video from YouTube.
- ```/instagram``` - to download video from Instagram.
- ```/crystalball``` - to answer your question.
- ```/topspotifyartist``` - to guess one of the top Spotify artists.
- ```/contact``` - to contact the Admin/Creator.
- ```/report``` - to report an issue to the Admin.
