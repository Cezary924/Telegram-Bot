<div align="center">
   <h1>Moduły</h1>
   <h3>🧩</h3>
   <h3>Jak napisać moduł dla Bota</h3>
   <a href="https://github.com/Cezary924/Telegram-Bot/blob/master/README.pl-pl.md" target="__blank"><img alt="Odznaka z napisem 'Docs Readme' - odnośnik prowadzi do głównego pliku README" src="https://img.shields.io/badge/Docs-Readme-222222?style=for-the-badge&logo=markdown&logoColor=30A3E6"></a><br/><br/>
   <a href="https://github.com/Cezary924/Telegram-Bot/blob/master/MODULES.md" target="__blank"><img alt="Odznaka z napisem 'Lang 🇬🇧' - odnośnik prowadzi do pliku MODULES po angielsku" src="https://img.shields.io/badge/Lang-🇬🇧-012169?style=for-the-badge"></a>
   <a href="https://github.com/Cezary924/Telegram-Bot/blob/master/MODULES.pl-pl.md" target="__blank"><img alt="Odznaka z napisem 'Lang 🇵🇱' - odnośnik prowadzi do pliku MODULES po polsku" src="https://img.shields.io/badge/Lang-🇵🇱-dc143c?style=for-the-badge"></a>
</div><br/>

## ✨ Główne założenia

- Moduł to katalog 📁
- Wszystko, czego moduł potrzebuje, leży w nim 📦

## 📁 Struktura

```
src2/modules/
   internal/     dostarczane z Botem, nie da się ich wyłączyć, dostają rozszerzony kontekst
   external/     opcjonalne funkcje, da się je wyłączyć, dostają podstawowy kontekst
```

Przykładowy moduł może wyglądać tak:

```
modules/external/crystalball/
   __init__.py
   module.py
   locales/en.yaml
   locales/pl.yaml
   tests/test_module.py
```

```python
# module.py
from core.api import Ctx, Module, Role

module = Module(name="crystalball")


@module.command("crystalball", role=Role.USER)
def crystalball(ctx: Ctx) -> str:
    return ctx.t("answer")
```

```yaml
# locales/en.yaml
name: Crystal ball
description: Answers your question
commands.crystalball: Ask the crystal ball
answer: Ask again later
```

> Nazwa katalogu, nazwa w manifeście i prefiks tabel muszą się zgadzać. Loader odrzuca moduł, którego ```module.py```
> deklaruje inną nazwę niż jego katalog.

## ⚙️ Manifest

```python
module = Module(
    name="reminder",  # małe litery, cyfry, podkreślenia
    requires=["downloader"],  # inne moduły, które muszą się załadować wcześniej
    tokens=["spotify_id"],  # jedyne sekrety, które ten moduł może odczytać
    features=["reminder"])  # wpisy do ekranów pomocy i listy funkcji
```

> Moduł potrzebujący paczki z pip dokłada własny ```requirements.txt``` obok ```module.py```. Gdy paczki brakuje, moduł
> jest pomijany z linią w logu, a Bot wstaje bez niego.

## 🧩 Deklaracje

| Dekorator                                                           | Co robi                                                                   |
|---------------------------------------------------------------------|---------------------------------------------------------------------------|
| ```@module.command("nazwa", role=, description=, is_background=)``` | rejestruje ```/nazwa``` i dodaje ją do menu komend w Telegramie           |
| ```@module.callback("akcja", role=, is_background=)```              | obsługuje przycisk ```moduł:akcja:argumenty```                            |
| ```@module.view("nazwa")```                                         | buduje ekran, który rdzeń umie odtworzyć przy cofaniu                     |
| ```@module.state("nazwa", role=, is_background=)```                 | przejmuje zwykłe wiadomości, gdy użytkownik siedzi na ekranie ```nazwa``` |
| ```@module.match(predykat, priority=, role=, is_background=)```     | przejmuje wiadomości pasujące do ```predykat(text)```                     |
| ```@module.job(interval=, name=)```                                 | uruchamia się co ```interval``` sekund we własnym wątku                   |

- ```role``` domyślnie wynosi ```Role.GUEST```.
- ```is_background=True``` przenosi handler na osobny wątek — używaj do wszystkiego, co trwa, jak pobieranie czy
  odpytywanie zdalnego API.
- Matchery są sortowane po priorytecie malejąco, potem po nazwie modułu i kolejności deklaracji, więc wynik nie zależy
  od kolejności ładowania modułów.

## 🖥️ Ekrany

Widok z nazwą jest ekranem: trafia na stos nawigacji użytkownika, dostaje przycisk powrotu i da się go odtworzyć, gdy
użytkownik go naciśnie.

```python
@module.command("reminder", role=Role.USER)
def command_reminder(ctx: Ctx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: Ctx) -> View:
    return View(
        text=ctx.t("menu.text"),
        path=[ctx.t("menu.title")],
        buttons=[Button(ctx.t("menu.set"), "set"),
                 Button(ctx.t("menu.manage"), "manage")])
```

Handler zwraca to, co ma się pokazać:

- ```str``` albo ```View``` bez nazwy — pojedyncza wiadomość,
- ```View``` zwrócony przez funkcję z ```@module.view``` - ekran,
- ```None``` - handler zrobił już wszystko, co chciał.

Komenda zaczyna nawigację od nowa, callback schodzi o poziom niżej. Dwukrotne uruchomienie tej samej komendy otwiera
więc jej ekran ponownie, zamiast układać go na stosie. Przycisk uruchamiający komendę to
```Button.command(tekst, "help")``` - obsługuje go rdzeń, więc żaden moduł nie musi znać akcji innego modułu.

> Przycisk powrotu należy do rdzenia: kasuje bieżący ekran, zdejmuje go ze stosu i odtwarza rodzica. Moduły nie piszą
> kodu nawigacji.

## 🎒 Kontekst

Każdy handler przyjmuje jeden argument.

```python
ctx.t("klucz", name="wartość")  # teksty tego modułu, w języku użytkownika
ctx.t("core:yes_button")  # inna przestrzeń nazw, wskazana wprost
ctx.user  # id, imię, ranga, język, zgoda
ctx.text  # treść przychodzącej wiadomości
ctx.forwarded_from  # kto napisał przesłaną wiadomość, o ile użytkownik na to pozwolił
ctx.arguments  # argumenty z danych callbacku
ctx.state["step"] = "2"  # na użytkownika i moduł, trzymane w bazie
ctx.nav  # stos nawigacji, ograniczony do tego modułu
ctx.db  # własne tabele tego modułu
ctx.token("spotify_id")  # tylko sekrety zadeklarowane w manifeście
ctx.log("Reminder set")  # "Reminder set: First (1)."
ctx.close_screen()  # zamyka ekran, na którym użytkownik kliknął
ctx.send_file(path, "video")  # audio, document, photo, video albo voice
ctx.file_limit  # największy plik, jaki Telegram pozwala wysłać botowi
with ctx.workspace() as path:  # katalog tymczasowy, kasowany także po błędzie
    ...
```

Moduły wewnętrzne dostają więcej:

```python
ctx.users, ctx.settings, ctx.registry, ctx.config  # repozytoria rdzenia i konfiguracja
ctx.version  # wersja Bota, odczytana z gita przy starcie
ctx.languages  # wszystkie języki Bota, jako pary (kod, etykieta)
ctx.use_language("pl")  # zmienia język użytkownika, razem z tym kontekstem
ctx.language_of(user_id)  # język innego użytkownika
ctx.text_for(user_id, "klucz")  # tekst w języku innego użytkownika
ctx.notify(user_id, view)  # pisze do innego użytkownika, z jego ustawieniem powiadomień
```

> Moduły zewnętrzne nie mają tych atrybutów w ogóle.

Handler zadania w tle przyjmuje zamiast powyższego ```JobCtx```: ```db```, ```t(klucz, język)```,
```language_of(user_id)```,
```send(user_id, view)``` i ```log```.

## 🌐 Teksty

Każdy moduł ma własną przestrzeń nazw, więc ```key1``` w jednym module i ```key1``` w drugim to dwa różne teksty.
Zagnieżdżony YAML spłaszcza się kropką:

```yaml
menu:
  title: Reminders     # menu.title
```

Każdy moduł potrzebuje klucza ```name``` i ```description``` - ```/help``` i ```/features``` wypisują moduły jako
```/komenda - Name - Description```.

Języki Bota to pliki w ```core/locales```. Moduł dostarcza jeden plik na język, ani mniej ani więcej, a ```en.yaml```
jest awaryjnym źródłem dla każdego innego języka. Każdy język nazywa sam siebie we własnym pliku, pod kluczem
```language_label```, więc nowy język dodaje się w jednym miejscu.

> Brakujący klucz nie jest błędem. Użytkownik zobaczy ```reminder:menu.title```.

## 🗄️ Tabele

Moduł jest właścicielem tabel z prefiksem ```module_<nazwa>_```. Umieść je w ```schema.sql``` obok ```module.py```, a
loader założy je przy starcie:

```sql
CREATE TABLE IF NOT EXISTS module_reminder_reminders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date TEXT NOT NULL
);
```

> Warto mieć klucz obcy: skasowanie użytkownika czyści wtedy również wiersze modułu, a dokładnie tego wymaga usuwanie
> danych na żądanie.

Nie ma wersjonowania schematu. Zmiana tabeli, która już gdzieś istnieje, to ręczna migracja instancji.

## 🧪 Testy

Moduł nie potrzebuje własnej konfiguracji testów. Każdy test dostaje dwa fixture'y:

```python
from core.testing import make_message


def test_the_menu_opens(app, bot):
    app.router.handle_message(make_message("/reminder"))
    assert bot.last.text.startswith("*🔔 Przypomnienia:*")
```

- ```app``` - Bot z załadowanymi wszystkimi modułami wewnętrznymi, pustą bazą i atrapą Telegrama,
- ```bot``` - to, co Bot wysłał, zedytował i skasował w trakcie testu.

> ```core.testing``` udostępnia też ```make_message```, ```make_callback```, ```make_storage```, ```FakeBot``` i
> ```not_none``` dla testów, które budują własne części. Testy nie potrzebują sieci ani pliku bazy.

## 🔌 Wyłączanie modułów

```config/modules.yaml``` wypisuje wyłącznie to, co ma być wyłączone:

```yaml
youtube: false
```

- Brak pliku oznacza, że wszystko jest włączone.
- Moduł nieobecny w pliku jest włączony.
- Modułów wewnętrznych nie da się wyłączyć.

## ✅ Kontrakt

```core/contract.py``` sprawdza każdy moduł za pomocą poniższego zestawu testów:

- nazwa w manifeście zgadza się z katalogiem, nic nie wymaga samego siebie,
- jest jeden plik językowy na każdy język Bota, każdy z tymi samymi kluczami co ```en.yaml```, w tym ```name```,
  ```description``` oraz klucz opisu każdej komendy,
- nazwy callbacków zostawiają miejsce na argumenty w ramach limitu 64 bajtów Telegrama,
- ```schema.sql``` tworzy wyłącznie obiekty z prefiksem modułu,
- moduł zewnętrzny importuje z rdzenia tylko ```core.api``` i ```core.testing```, a z innych modułów tylko te wypisane w
  ```requires```,
- moduł ma katalog ```tests```.
