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
src/modules/
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

module = Module(name="crystalball", is_guarded=True)


@module.command("crystalball")
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
    uses=["bodytracker"],  # inne moduły, z którymi współpracuje, gdy są, a bez nich działa i tak
    formerly=["unitconverter"],  # nazwy, które miał wcześniej i których dane przejmuje
    tokens=["service_key"],  # jedyne sekrety, które ten moduł może odczytać
    config_keys=["service_url"],  # jedyne wpisy z config.yaml, które może odczytać
    notifications="name",  # klucz tekstu, pod którym jego powiadomienia widać w /settings
    is_guarded=True,  # tylko dla osób wpuszczonych przez admina albo dla wszystkich z listy domyślnej (obecnie: admini)
    is_assistant=True,  # może przekazać akcje i kontekst innych modułów modelowi językowemu
    place=30,  # jego miejsce wszędzie, gdzie widać listę modułów - /features, /settings, komendy, panel admina
    icons={'name': "🔔"},  # stawiana przed tekstem, w każdym języku
    endings={'saved': "✅"})  # stawiana po nim
```

> To, co moduł wysyła sam z siebie - ```ctx.notify``` i ```JobCtx.send``` - jest powiadomieniem: użytkownik decyduje w
> ```/settings```, czy ma dzwonić, i może zablokować wszystkie powiadomienia naraz. Wyciszony moduł dalej dostarcza
> wiadomości, tylko po cichu. Odpowiedź na coś, co użytkownik zrobił, dzwoni zawsze.

> Moduł po zmianie nazwy zachowuje to, co ludzie mają: przy starcie rdzeń przenosi dostępy, prośby, stan,
> powiadomienia, ekrany i tabele ```module_<stara>_``` każdej nazwy z ```formerly``` na nową, nie ruszając tego, co nowa
> nazwa już ma. Wpis w ```modules.yaml``` pod starą nazwą jest przepisywany na nową, dopóki nowej tam nie ma, więc
> wyłączony moduł zostaje wyłączony. Moduł, którego stara nazwa wciąż ma własny katalog, jest pomijany, więc nigdy nie
> zabierze tego, co należy do innego modułu.

> Moduł potrzebujący paczki z pip dokłada własny ```requirements.txt``` obok ```module.py```, a kontrakt odrzuca moduł
> importujący coś, czego nie zadeklarował. Liczy się nazwa pakietu, nie nazwa importu, więc ```bs4``` deklaruje się jako
> ```beautifulsoup4```. Gdy paczki brakuje, moduł jest pomijany z linią w logu, a Bot wstaje bez niego.

## 🧩 Deklaracje

| Dekorator                                                                                 | Co robi                                                                   |
|-------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| ```@module.command("nazwa", role=, description=, is_background=)```                       | rejestruje ```/nazwa``` i dodaje ją do menu komend w Telegramie           |
| ```@module.callback("akcja", role=, is_background=)```                                    | obsługuje przycisk ```moduł:akcja:argumenty```                            |
| ```@module.view("nazwa", parent=, title=)```                                              | buduje ekran, umieszczony pod ```parent``` w drzewie modułu               |
| ```@module.settings(role=)```                                                             | buduje ekran ustawień modułu, widoczny w ```/settings```                  |
| ```@module.state("nazwa", role=, is_background=)```                                       | przejmuje zwykłe wiadomości, gdy użytkownik siedzi na ekranie ```nazwa``` |
| ```@module.match(predykat, priority=, role=, is_background=)```                           | przejmuje wiadomości pasujące do ```predykat(text)```                     |
| ```@module.job(interval=, name=, is_aligned=)```                                          | uruchamia się co ```interval``` sekund we własnym wątku                   |
| ```@module.action("nazwa", parameters=, optional=, description=, role=, is_confirmed=)``` | pozwala asystentowi zrobić ```nazwa``` za użytkownika                     |
| ```@module.context()```                                                                   | mówi asystentowi, co moduł wie o użytkowniku                              |
| ```@module.expose("nazwa", is_writing=)```                                                | udostępnia ```nazwa``` modułom, które go wymagają albo używają            |
| ```@module.form("nazwa", pytania, parent=, title=)```                                     | zadaje pytania po kolei i przekazuje dalej odpowiedzi                     |

- ```role``` domyślnie wynosi ```Role.GUEST```.
- Są trzy rangi: ```Role.BANNED```, ```Role.GUEST``` i ```Role.ADMIN```. Każdy nowy człowiek jest gościem.
- Moduł z ```is_guarded=True``` wymaga dostępu w całości - każda komenda, przycisk, odpowiedź i jego ustawienia. Admin
  daje jednej osobie jeden moduł albo dopisuje moduł do listy domyślnej dla wszystkich. Bez dostępu osoba może o niego
  poprosić, a admini dostają prośbę z przyciskami Daj dostęp i Odmów. Handler z ```role=Role.ADMIN``` wymaga do tego
  jeszcze rangi.
- Wiadomość, która nie jest tekstem - zdjęcie, głosówka, lokalizacja i tak dalej - omija komendy i ekrany, i trafia
  tylko do matcherów, które wymieniają jej rodzaj w ```media```, np. ```media=("photo", "voice")```, bez predykatu. Gdy
  nikt jej nie weźmie, użytkownik słyszy, że Bot jej nie rozumie.
- Matcher modułu chronionego milczy wobec osób bez dostępu, a wiadomość idzie dalej, jakby modułu nie było. Prośbę o
  dostęp proponuje tylko komenda, więc moduł łapiący zwykłe wiadomości nikogo nie zaczepia.
- Komenda tylko dla admina jest ukryta: nie trafia do menu komend Telegrama ani na ekran pomocy.
- ```is_background=True``` przenosi handler na osobny wątek — używaj do wszystkiego, co trwa, jak pobieranie czy
  odpytywanie zdalnego API.
- ```is_aligned=True``` nakazuje czekać zadaniu do najbliższej pełnej wielokrotności interwału, więc sprawdzanie co 60
  sekund trafia w pełną minutę zamiast dryfować od momentu startu Bota.
- Matchery są sortowane po priorytecie malejąco, potem po nazwie modułu i kolejności deklaracji, więc wynik nie zależy
  od kolejności ładowania modułów.

## 🖥️ Ekrany

Widok z nazwą jest ekranem. Każdy mówi, gdzie stoi, przy pomocy pola ```parent```, i jak go nazwać, dzięki ```title```

- to klucz tekstu, jak wszystko, co czyta użytkownik. Ekrany modułu tworzą drzewo, a rdzeń po nim chodzi:
  przycisk powrotu i to, gdzie powrót ląduje, biorą się z drzewa, nigdy z tego, co użytkownik naciskał wcześniej.

```python
@module.command("reminder")
def command_reminder(ctx: Ctx) -> View:
    return menu(ctx)


@module.view("menu")
def menu(ctx: Ctx) -> View:
    return View(
        text=ctx.t("menu.text"),
        buttons=[Button(ctx.t("menu.set"), "set"),
                 Button(ctx.t("menu.manage"), "manage")])


@module.view("set", parent="menu", title="menu.set")
def ask_content(ctx: Ctx) -> View:
    return View(text=ctx.t("set.question"))
```

Handler zwraca to, co ma się pokazać:

- ```str``` albo ```View``` bez nazwy — pojedyncza wiadomość,
- ```View``` zwrócony przez funkcję z ```@module.view``` - ekran,
- ```None``` - handler zrobił już wszystko, co chciał.

```View``` z ```photo=``` - bajtami obrazka, na przykład wykresu narysowanego w pamięci - wysyła się jako ten obrazek z
tekstem pod nim. Jako ekran zajmuje miejsce poprzedniego jak każdy inny ekran, a jego przyciski zostają pod obrazkiem.
Tekst obrazka może mieć najwyżej 1024 znaki, więc rdzeń zostawia nagłówek, pierwszy wiersz i najnowsze wiersze, a w
miejscu reszty stawia ```…```.

Ekran niesie jedną wiadomość naraz. Naciśnięcie przycisku przepisuje ją w miejscu, więc chodzenie po module nic nie
dokłada do czatu. Wpisana wiadomość - komenda, odpowiedź na pytanie - to co innego: użytkownik coś napisał, więc ekran
znika i zostaje napisany od nowa pod tym, co napisał, i zostaje ostatnią rzeczą w czacie. Dwukrotne uruchomienie tej
samej komendy otwiera jej ekran na dole, zamiast zostawiać dwa.

Przycisk uruchamiający komendę to ```Button.command(tekst, "help")``` - obsługuje go rdzeń, więc żaden moduł nie musi
znać akcji innego modułu.

> Wstecz, Menu i Zamknij należą do rdzenia. Rysuje je według głębokości, odtwarza rodzica z drzewa i pamięta argument,
> z jakim każdy ekran był ostatnio otwarty, więc powrót do trzeciej strony listy wraca na trzecią stronę. Moduły nie
> piszą kodu nawigacji.

Odpowiedź, z której moduł nie umie skorzystać, nie jest osobną wiadomością - ```ctx.retry``` pyta tym samym ekranem
jeszcze raz, ale tym razem uwzględnia problem:

```python
@module.state("set")
def take_content(ctx: Ctx) -> View:
    if not ctx.text.strip():
        return ctx.retry(ctx.t("set.empty"))
    return save(ctx)
```

### Formularze

Kilka pytań z rzędu to formularz. Moduł je wypisuje i dostaje wszystkie odpowiedzi naraz; ekrany, odpowiedzi trzymane
między wiadomościami, przyciski i ```ctx.retry``` należą do rdzenia, więc każdy moduł pyta tak samo:

```python
from core.api import Answers, Question


@module.form("body", [Question("sex", "choice", choices=("female", "male")),
                      Question("height", "height", low=100, high=250),
                      Question("when", "moment", back=48)], parent="menu", title="manual")
def counted(ctx: Ctx, answers: Answers) -> View:
    return View(text=ctx.t("result", height=ctx.profile.height(answers['height'])))


@module.callback("count")
def count(ctx: Ctx) -> View:
    return ctx.form("body", offered=ctx.ask("bodytracker", "latest"))
```

- ```number``` przyjmuje przecinek tak samo jak kropkę oraz ```%``` na końcu i musi się zmieścić między ```low``` a
  ```high```. ```parse=``` zamienia to sprawdzenie na własne modułu: dostaje tekst i dotychczasowe odpowiedzi, a zwraca
  wartość albo ```None```, i wtedy pokazuje się tekst wskazany w ```problem=```. ```Problem("klucz", {'low': 1})```
  wskazuje zamiast tego dokładny problem.
- ```weight``` i ```height``` wpisuje się w jednostkach wybranych w Ustawieniach > O mnie - kilogramach albo funtach,
  centymetrach albo stopach i calach - a do modułu zawsze trafiają w kilogramach i centymetrach, łącznie z ```low``` i
  ```high```. ```{unit}``` w pytaniu podaje jednostkę, a ```ctx.profile.weight(kg)``` i ```ctx.profile.height(cm)```
  pokazują wartość z powrotem tak samo.
- ```text``` jest przycinany i musi mieć od ```low``` (co najmniej 1) do ```high``` znaków.
- Na ```choice``` odpowiada się przyciskami opisanymi tekstami ```<klucz>.<wybór>```, a na ```moment``` przyciskami
  Teraz, 30 min, 1 h i 2 h temu albo wpisanym ```21:30```, ```21.30```, ```2026-10-30 21:30```, ```30.10.2026 21:30```
  lub ```30.10 21:30``` w bieżącym roku, nigdy z przyszłości i najwyżej ```back``` godzin wstecz - ```back=None```
  pozwala cofnąć się dowolnie daleko. ```read_moment(text, now, is_future=)``` czyta te same zapisy na potrzeby
  własnych sprawdzeń modułu.
- ```clear=``` dodaje przycisk opisany tym kluczem tekstu, który odpowiada ```None``` - na odpowiedź, której
  użytkownik woli nie podawać. ```is_needed=``` dostaje dotychczasowe odpowiedzi i pomija pytanie, gdy zwróci
  ```False```, więc formularz pyta o ostatni drink tylko wtedy, gdy był więcej niż jeden.
- Samo pytanie to tekst ```ask.<klucz>``` albo ```text=```. Ono i ```problem``` mogą użyć jako placeholdera każdej
  dotychczasowej odpowiedzi albo wartości podanej w ```known``` - ```Napisz swoją wagę w {unit}```.
- O odpowiedzi z ```known``` formularz nie pyta. Te z ```offered``` pochodzą z tego, co użytkownik zapisał: rdzeń raz
  pyta, czy ich użyć, nie pokazując ich, i pomija puste, te, których żadne pytanie by nie przyjęło, oraz całą propozycję,
  gdy nic w niej nie odpowiada na pytanie. Podawaj tylko to, co jest na tyle świeże, żeby użyć tego bez zaglądania.
- Dane z różnych miejsc proponuje się osobno: ```offered=[("offer.body", body), ("offer.drinks", drinks)]``` pyta o
  każdą grupę jej własnym tekstem, więc użytkownik może wziąć jedną, a drugą wpisać.
- ```Answers``` trzyma wartości w ```values```, klucze wpisane ręcznie w ```typed``` i klucze odrzuconych grup w
  ```declined```.
  ```answers.new(klucze)``` to to, co użytkownik wpisał o sobie - to, co można zaproponować do zapisania.
- Formularz należy do ekranu, z którego go otwarto: Wstecz przy pierwszym pytaniu wraca właśnie tam. Wyjście z niego -
  komendą, innym ekranem albo ```ctx.close_screen()``` - zapomina dotychczasowe odpowiedzi, więc nic wpisanego w połowie
  nie czeka na późniejszą wiadomość.

Moduł z własnymi opcjami deklaruje jeden ekran ustawień. Bot pokazuje go w ```/settings``` pod Modułami, po stronie
naraz, a sam ekran stoi pod tą listą: nagłówek to, np. ```⚙️ Ustawienia > 🧩 Moduły > 📥 Pobieracz```, a Wstecz wraca
do listy. Otwarty przez ```Button.settings``` z ekranu samego modułu, Wstecz i Menu wracają do tego modułu. Ekrany
głębiej w
ustawieniach dostają ```parent="settings"```:

```python
@module.settings()
def settings(ctx: Ctx) -> View:
    return View(text=ctx.t("settings.text"), buttons=[Button(ctx.t("settings.format"), "format")])
```

## 🤖 Asystent

Moduł może pozwolić asystentowi - modułowi ```llm``` - działać w sobie w imieniu osoby, która z nim rozmawia. Akcja to
funkcja, którą model językowy może wywołać, z argumentami, które sam uzupełnia:

```python
from core.api import Ctx, Module, Outcome


@module.action("add", parameters={'content': str, 'date': str}, is_confirmed=True)
def act_add(ctx: Ctx, content: str, date: str) -> Outcome:
    problem = wrong_content(ctx, content)
    if problem:
        return Outcome.refused(problem)
    return Outcome.ask(ctx.t("add_sure") + "\n" + details(ctx, content, date), lambda: added(ctx, content, date))


@module.action("list")
def act_list(ctx: Ctx) -> Outcome:
    return Outcome.done([{'reminder_id': row['id'], 'date': row['date']} for row in reminders_of(ctx)])
```

- Akcja działa z ```Ctx``` osoby, która rozmawia, jak każdy handler. Model wybiera tylko argumenty, nigdy osobę, więc
  nic, co wyśle, nie dosięgnie cudzych danych.
- Argumenty to ```str```, ```int```, ```float``` albo ```bool``` i każdy jest wymagany, chyba że jest wymieniony w
  ```optional=["date"]``` - wtedy ten, którego model nie poda, przychodzi jako ```None```. Rdzeń zamienia ```"3"``` na
  ```3``` i odrzuca to, co nie pasuje, zanim moduł to zobaczy.
- Moduł sprawdza wartości tymi samymi funkcjami, których używają jego ekrany. To, co ```ctx.retry``` pokazuje na
  ekranie, ```Outcome.refused``` oddaje modelowi, a ten może dopytać osobę jeszcze raz. ```past_moment(text)``` czyta
  godzinę tak jak pytanie ```moment``` i oddaje ją w ISO albo ```None```, gdy jest zła lub jeszcze nie minęła.
- Parametr nazywający użytkownika - ```user```, ```user_id```, ```other_user``` - zostaje odrzucony przy ładowaniu
  modułu, więc akcji nigdy nie da się wycelować w kogoś innego.
- ```Outcome.done(result)``` to odpowiedź - krótki tekst albo lista lub słownik prostych wartości do przeczytania przez
  model.
- ```Outcome.ask(question, then)``` mówi, co by się stało. Z ```is_confirmed=True``` osoba dostaje pytanie z przyciskami
  ✅ i ❌. ✅ uruchamia akcję jeszcze raz od początku, więc wszystko jest sprawdzane ponownie, i dopiero wtedy wywołuje
  ```then()```, którego tekst zajmuje miejsce pytania. Bez ```is_confirmed``` rdzeń wywołuje ```then()``` od razu.
- Akcja jest oferowana tylko osobom, które mogą korzystać z jej modułu, a z ```role=``` tylko tym z odpowiednią rangą.
  Moduł wyłączony albo taki, który się nie załadował, nie oferuje nic.
- Model zna akcję jako ```moduł_akcja```, np. ```reminder_add```. To, co o niej czyta, to teksty jak wszystkie inne:
  ```actions.add``` opisuje akcję, a ```parameters.content``` parametr, wspólny dla wszystkich akcji modułu.
  ```description=``` wskazuje inny klucz dla akcji.

Moduł może też powiedzieć asystentowi, co wie o osobie - kilka linijek, które ten może sam poruszyć:

```python
@module.context()
def summary(ctx: Ctx) -> str:
    return "\n".join(escape(row['date'] + " - " + row['content']) for row in upcoming(ctx))
```

Podsumowanie jest znacznikami jak każdy inny tekst, więc wszystko, co napisał użytkownik, jest escapowane. Rdzeń zamienia
je na zwykły tekst i zostawia najwyżej pięć linijek. W ustawieniach asystenta osoba decyduje, w których modułach może on
czytać i działać.

> Tylko moduł z ```is_assistant=True``` w manifeście dostaje ```ctx.assistant```: ```modules()```, ```actions()```,
> ```act(module, action, arguments, is_confirmed=)``` i ```context(module)```, zawsze dla ```ctx.user```.

## 🎒 Kontekst

Każdy handler przyjmuje jeden argument.

```python
ctx.t("klucz", name="wartość")  # teksty tego modułu, w języku użytkownika
ctx.t("core:yes_button")  # inna przestrzeń nazw, wskazana wprost
ctx.user  # id, imię, ranga, język, zgoda
ctx.text  # treść przychodzącej wiadomości albo podpis zdjęcia, filmu i tak dalej
ctx.kind  # co przyszło: "text", "photo", "voice", "location"... tak, jak nazywa to Telegram
ctx.forwarded_from  # kto napisał przesłaną wiadomość, o ile użytkownik na to pozwolił
ctx.arguments  # argumenty z danych callbacku
ctx.state["step"] = "2"  # na użytkownika i moduł, trzymane w bazie
ctx.nav  # gdzie jest użytkownik i co zapamiętał każdy ekran tego modułu
ctx.db  # własne tabele tego modułu
ctx.token("service_key")  # tylko sekrety zadeklarowane w manifeście
ctx.has_token("service_key")  # czy zadeklarowany sekret w ogóle jest ustawiony
ctx.setting("service_url")  # zadeklarowany wpis z config.yaml, None gdy go brak
ctx.has_module("bodytracker")  # czy wymagany albo używany moduł jest załadowany i dostępny dla użytkownika
ctx.ask("bodytracker", "latest")  # to, co tamten moduł udostępnia jako "latest", None gdy has_module daje False
ctx.profile  # płeć, data urodzenia, wiek i jednostki, wspólne dla wszystkich modułów, wszystko opcjonalne
ctx.set_profile(sex="female")  # zmienia wspólne dane, sprawdzając każdą wartość
ctx.form("body", known={}, offered={})  # zaczyna formularz: pomija znane, proponuje zapisane, także grupami
message_id = ctx.reply_live(tekst)  # wiadomość, którą moduł może potem przepisać, is_silent=True wysyła ją po cichu
ctx.edit(message_id, tekst)  # przepisuje ją, False gdy Telegram odmówi
ctx.remove(message_id)  # usuwa ją, False gdy Telegram odmówi
ctx.remove_buttons(message_id)  # zabiera jej przyciski, a tekst zostawia, False gdy Telegram odmówi
ctx.log("Reminder set")  # "Reminder set: First (1)."
ctx.retry(problem)  # ten sam ekran jeszcze raz
ctx.close_screen()  # zamyka ekran, na którym użytkownik kliknął, kończąc przepływ
ctx.send_file(path, "video")  # audio, document, photo, video albo voice
ctx.send_album(pictures)  # zdjęcia w albumach po maksymalnie dziesięć
ctx.file_limit  # największy plik, jaki Telegram pozwala wysłać botowi
ctx.download(file_id)  # bajty pliku, który przysłał użytkownik, None gdy Telegram odmówi
ctx.download_limit  # największy plik, jaki Telegram pozwala botowi pobrać
with ctx.workspace() as path:  # katalog tymczasowy, kasowany także po błędzie
    ...
```

Moduły wewnętrzne dostają więcej:

```python
ctx.users, ctx.settings, ctx.registry, ctx.config  # repozytoria rdzenia i konfiguracja
ctx.access, ctx.can_use("reminder")  # kto może korzystać z którego modułu
ctx.version  # wersja Bota, odczytana z gita przy starcie
ctx.languages  # wszystkie języki Bota, jako pary (kod, etykieta)
ctx.use_language("pl")  # zmienia język użytkownika, razem z tym kontekstem
ctx.language_of(user_id)  # język innego użytkownika
ctx.text_for(user_id, "klucz")  # tekst w języku innego użytkownika
ctx.notify(user_id, view)  # pisze do innego użytkownika jako powiadomienie
```

> Moduły zewnętrzne nie mają tych atrybutów w ogóle.

Handler zadania w tle przyjmuje zamiast powyższego ```JobCtx```: ```db```, ```t(klucz, język)```,
```language_of(user_id)```,
```send(user_id, view)``` i ```log```.

## 🤝 Współpraca modułów

```requires``` czyni moduł częścią innego: bez niego moduł jest pomijany. ```uses``` to luźniejsza więź - moduł ładuje
się tak czy inaczej i dopiero w działaniu sprawdza, czy ten drugi jest na miejscu. Moduł dzieli się tym, co inni mają
czytać, przez udostępnioną funkcję:

```python
# bodytracker/module.py
module = Module(name="bodytracker")


@module.expose("latest")
def latest(ctx: Ctx) -> dict | None:
    return {'weight': last_weight(ctx), 'height': height_of(ctx)}
```

```python
# bmi/module.py
module = Module(name="bmi", uses=["bodytracker"])


@module.callback("count")
def count(ctx: Ctx) -> View:
    return ctx.form("body", offered=ctx.ask("bodytracker", "latest"))
```

- Udostępniona funkcja działa jako moduł, który ją udostępnia: dostaje własny ```ctx``` dla tego samego użytkownika,
  więc czyta własne tabele, a jako kolejne argumenty to, co w ```ctx.ask``` padło po nazwie.
- ```ctx.has_module``` i ```ctx.ask``` dają ```False``` i ```None```, gdy drugi moduł jest wyłączony, nie załadował się
  albo jest strzeżony, a użytkownik nie ma do niego dostępu. ```ctx.ask``` daje ```None``` także wtedy, gdy udostępniona
  funkcja zawiedzie - błąd trafia do logu, a pytający moduł działa dalej. Podanie modułu, którego nie ma ani
  w ```requires```, ani w ```uses```, rzuca ```PermissionError```, a pytanie o coś, czego nie udostępnia, rzuca
  ```LookupError```.
- Moduły instalują się po tych, których wymagają albo używają. Moduł, którego wymagany moduł nie zdołał się
  zainstalować, też jest pomijany; ten, któremu zabrakło używanego, po prostu działa bez niego.
- Dwa moduły mogą używać siebie nawzajem. Moduł nie może używać samego siebie ani jednocześnie wymagać i używać tego
  samego modułu.
- Udostępniona funkcja może przyjmować argumenty i zmieniać dane swojego modułu - tak wynik proponuje zapisanie w
  dzienniku tego, co użytkownik wpisał. Taką funkcję deklaruje się z ```is_writing=True```, a rdzeń uruchamia ją tylko
  po naciśnięciu przycisku albo po potwierdzeniu akcji asystenta - wołana inaczej rzuca ```PermissionError```.
- To, co opisuje użytkownika, a nie jeden moduł - płeć, data urodzenia, jednostki - żyje w ```ctx.profile```, a nie w
  osobnym module, więc każdy moduł czyta i zapisuje te same dane.
- Moduł może importować z modułów, których używa, ale taki import zawodzi, gdy tamtego katalogu nie ma. Lepiej sięgać po
  ```ctx.ask```, a importować tylko to, czego brak niczego nie psuje, wewnątrz funkcji, która tego potrzebuje.

## 🌐 Teksty

Każdy moduł ma własną przestrzeń nazw, więc ```key1``` w jednym module i ```key1``` w drugim to dwa różne teksty.
Zagnieżdżony YAML spłaszcza się kropką:

```yaml
menu:
  title: Reminders     # menu.title
```

Teksty zawierają wyłącznie słowa. Emotka otwierająca albo zamykająca tekst należy do ```icons``` i ```endings``` w
manifeście, więc jest wpisana raz zamiast raz na język, a tłumaczenie nie może się od niej rozjechać. Kontrakt odrzuca
ikonę albo zakończenie dla klucza, który nie ma tekstu. Emotka w środku zdania zostaje w tekście.

Każdy moduł potrzebuje klucza ```name``` i ```description``` - ```/help``` i ```/features``` wypisują moduły jako
```/komenda - Name - Description```.

Języki Bota to pliki w ```core/locales```. Moduł dostarcza jeden plik na język, ani mniej ani więcej, a ```en.yaml```
jest awaryjnym źródłem dla każdego innego języka. Każdy język nazywa sam siebie we własnym pliku, pod kluczem
```language_label```, więc nowy język dodaje się w jednym miejscu.

> Brakujący klucz nie jest błędem. Użytkownik zobaczy ```reminder:menu.title```.

### Formatowanie

Tekst to jedna goła linijka słów, więc tłumaczenie wymaga wyłącznie słów. Kontrakt odrzuca tekst w cudzysłowie, tekst
połamany na linie oraz tekst z tagami albo Markdownem. Cała reszta należy do kodu - składa linie, dokleja dwukropek
wprowadzający wartość i decyduje, jak wygląda każda część:

```yaml
menu: Ustawione przez Ciebie przypomnienia
pick:
  text: Wybierz przypomnienie, którym chcesz zarządzać.
  page: Strona {page} z {pages}, łącznie {total}
labels:
  content: Treść
  date: Data
```

Wiadomość składana z kilku tekstów dostaje własną grupę, żeby części, które do siebie należą, stały razem. Główne zdanie
to ```text```, pogrubiony nagłówek to ```title```, a każda inna część nosi nazwę od tego, co dodaje -
```hint```, ```page```. Nazwy pól pokazywanych jako ```Etykieta: wartość``` trafiają do ```labels```. Wartość stojąca w
środku zdania zostaje placeholderem, ```Z tej strony {name}!```, a nie zdaniem przeciętym na pół wokół niej - inny język
może potrzebować innego szyku.

```python
from core.api import bold, escape, italic, labelled

labelled(ctx.t("menu"), len(rows))  # "Ustawione przez Ciebie przypomnienia: <i>3</i>"
ctx.t("pick.text") + "\n" + ctx.t("pick.page", page=italic(page), pages=italic(pages), total=italic(total))
ctx.t("done", role=italic(role))  # "Ranga została zmieniona na {role}", z rangą kursywą
Button(escape(row['content']), "one", row['id'])  # to, co napisał użytkownik, jako bezpieczny tekst
```

> Tekst nigdy nie kończy się dwukropkiem ani nie zawiera dwukropka ze spacją, a same słowa ```yes```, ```no```, ```on```
> i ```off``` YAML czyta jako prawdę i fałsz. Gdy zdanie ich potrzebuje, zostaje sformułowane inaczej albo podzielone.

Wiadomości wychodzą jako HTML. Wszystko, co trafia do ```ctx.t``` jako wartość, jest escapowane po drodze, więc imię w
rodzaju ```<Eve> & co``` albo nazwa użytkownika ```john_doe``` nie zepsują wiadomości. ```bold``` i ```italic```
escapują to, co owijają; ```escape``` służy do reszty, którą moduł skleja ręcznie. Tekst z ```ctx.t``` jest już
znacznikiem i nigdy nie jest escapowany drugi raz. Przyciski i menu komend Telegrama przyjmują czysty tekst - rdzeń sam
zdejmuje z nich znaczniki.

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

W testach ```ctx.ask``` rzuca to, co rzuciła udostępniona funkcja, zamiast tylko to zalogować, więc zepsute wołanie
między modułami oblewa test.

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

- nazwa w manifeście zgadza się z katalogiem, nic nie wymaga ani nie używa samego siebie i żaden moduł nie jest
  jednocześnie wymagany i używany,
- jest jeden plik językowy na każdy język Bota, każdy z tymi samymi kluczami co ```en.yaml```, w tym ```name```,
  ```description``` oraz klucz opisu każdej komendy,
- każda akcja ma tekst, który ją opisuje, i tekst dla każdego swojego parametru,
- każdy tekst to jedna goła linijka, bez cudzysłowów, łamania linii, tagów i Markdownu,
- nazwy callbacków zostawiają miejsce na argumenty w ramach limitu 64 bajtów Telegrama,
- ```schema.sql``` tworzy wyłącznie obiekty z prefiksem modułu,
- moduł zewnętrzny importuje z rdzenia tylko ```core.api``` i ```core.testing```, a z innych modułów tylko te wypisane w
  ```requires``` albo ```uses```,
- każdy pakiet, który moduł importuje poza katalogiem ```tests```, jest wypisany w jego ```requirements.txt```,
- moduł ma katalog ```tests```.
