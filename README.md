<div align="center">
   <h1>Telegram Bot</h1>
   <h3>🤖</h3>
   <h3>Multifunctional Telegram Bot</h3>
   <a href="https://t.me/Cezary924Bot" target="__blank"><img alt="Badge with a label 'Telegram Bot' - a link takes to a chat with Cezary924Bot on Telegram" src="https://img.shields.io/badge/Telegram-Bot-222222?style=for-the-badge&logo=telegram&logoColor=30A3E6"></a>
   <a href="https://github.com/Cezary924/Telegram-Bot/actions/workflows/ci.yml" target="__blank"><img alt="A badge with a label 'CI' - a link takes to the workflow runs on GitHub" src="https://img.shields.io/github/actions/workflow/status/Cezary924/Telegram-Bot/ci.yml?style=for-the-badge&label=CI"></a><br/><br/>
   <a href="https://github.com/Cezary924/Telegram-Bot/blob/master/README.md" target="__blank"><img alt="A badge with a label 'Lang 🇬🇧' - a link takes to README file in English" src="https://img.shields.io/badge/Lang-🇬🇧-012169?style=for-the-badge"></a>
   <a href="https://github.com/Cezary924/Telegram-Bot/blob/master/README.pl-pl.md" target="__blank"><img alt="A badge with a label 'Lang 🇵🇱' - a link takes to README file in Polish" src="https://img.shields.io/badge/Lang-🇵🇱-dc143c?style=for-the-badge"></a>
</div><br/>

## ⚙️ Installation & Configuration

1. Clone this repo.
2. Install required libraries with this command:

```
pip install -r requirements.txt
```

3. Create:
    - the ```config.yaml``` file in the *config* folder and write the following code to it:
   ```
   bot_name: your_bot_name
   github_repo: your_github_repo_name
   github_username: your_github_username
   telegram_username: your_telegram_username
   ```
   > Write the username without the ```@```. The person it belongs to becomes the first
   Administrator of the Bot, as long as there is no Administrator yet.
    - the ```tokens.yaml``` file in the *config* folder and write the following code to it:
   ```
   telegram: your_telegram_token
   telegram_beta: your_another_telegram_token
   ```

4. Install [ffmpeg](https://ffmpeg.org/download.html). Services that hand out video and sound as separate files -
   YouTube among them - cannot be downloaded without it.


## 🚀 Starting

1. To start the Bot, execute this command in the main directory:

```
python src/bot.py
```

> You can also add the ```beta``` argument at the end of the command shown above to use the secondary Telegram
> token.

2. Enjoy!

## 🧩 Modules

Every feature is a module - a directory the Bot loads on start. Feature modules can be turned off in
```config/modules.yaml```, core modules are always there.
> Writing your own module is described in [MODULES.md](MODULES.md).

## 🧱 Core modules

- Welcome and feature list 👋 (```/start```, ```/features```)
- Help and about 💬 (```/help```, ```/about```)
- Settings, language and notifications ⚙️ (```/settings```)
- Contact and reports 📨 (```/contact```, ```/report```)
- User management and Bot control 🛠️ (```/admin```)
> ```/admin``` is a hidden command, available to the Administrator only.

## ✨ Feature modules

- Video downloader 📥 (```/downloader```)
- Reminders 🔔 (```/reminder```)
- Unit converter 🧮 (```/unitconverter```)
- Guess Top Spotify Artist ᯤ (```/topspotifyartist```)
- Crystal ball 🔮 (```/crystalball```)
