<div align="center">
   <h1>Modules</h1>
   <h3>🧩</h3>
   <h3>How to write a module for the Bot</h3>
   <a href="https://github.com/Cezary924/Telegram-Bot/blob/master/README.md" target="__blank"><img alt="A badge with a label 'Docs Readme' - a link takes to the main README file" src="https://img.shields.io/badge/Docs-Readme-222222?style=for-the-badge&logo=markdown&logoColor=30A3E6"></a><br/><br/>
   <a href="https://github.com/Cezary924/Telegram-Bot/blob/master/MODULES.md" target="__blank"><img alt="A badge with a label 'Lang 🇬🇧' - a link takes to MODULES file in English" src="https://img.shields.io/badge/Lang-🇬🇧-012169?style=for-the-badge"></a>
   <a href="https://github.com/Cezary924/Telegram-Bot/blob/master/MODULES.pl-pl.md" target="__blank"><img alt="A badge with a label 'Lang 🇵🇱' - a link takes to MODULES file in Polish" src="https://img.shields.io/badge/Lang-🇵🇱-dc143c?style=for-the-badge"></a>
</div><br/>

## ✨ Main ideas

- A module is a directory 📁
- Everything a module needs lives inside it 📦

## 📁 Structure

```
src/modules/
   internal/     shipped with the Bot, cannot be turned off, get the advanced context
   external/     optional features, can be turned off, get the basic context
```

An example module may look like this:

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

> The directory name, the manifest name and the table prefix must all agree. The loader refuses a module whose
> ```module.py``` declares a different name than its directory.

## ⚙️ Manifest

```python
module = Module(
    name="reminder",  # lowercase letters, digits, underscores
    requires=["downloader"],  # other modules that must be loaded first
    uses=["bodytracker"],  # other modules it works with when they are there, and without them otherwise
    tokens=["service_key"],  # the only secrets this module can read
    config_keys=["service_url"],  # the only entries of config.yaml it can read
    notifications="name",  # the text key its notifications are listed under in /settings
    is_guarded=True,  # usable only by people an admin let in, or by everyone on the default list (currently: admins)
    is_assistant=True,  # may hand other modules' actions and context to a language model
    place=30,  # where it stands wherever modules are listed - /features, /settings, the commands, the admin panel
    icons={'name': "🔔"},  # put in front of a text, in every language
    endings={'saved': "✅"})  # put after it
```

> What a module sends on its own - ```ctx.notify``` and ```JobCtx.send``` - is a notification: the user decides in
> ```/settings``` whether it makes a sound, and can block every notification at once. A user who turned a module down
> still gets its messages, only silently. A reply to something the user did always makes a sound.

> A module that needs a pip package ships its own ```requirements.txt``` next to ```module.py```, and the contract
> refuses a module that imports something it did not declare. The name of the package counts, not the name of the
> import, so ```bs4``` is declared as ```beautifulsoup4```. When the package is missing, the module is skipped with a
> line in the log and the Bot starts without it.

## 🧩 Declarations

| Decorator                                                                                | What it does                                                      |
|------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| ```@module.command("name", role=, description=, is_background=)```                       | registers ```/name``` and adds it to the Telegram command menu    |
| ```@module.callback("action", role=, is_background=)```                                  | handles the button ```module:action:arguments```                  |
| ```@module.view("name", parent=, title=)```                                              | builds a screen, placed under ```parent``` in the module tree     |
| ```@module.settings(role=)```                                                            | builds the module's settings screen, listed in ```/settings```    |
| ```@module.state("name", role=, is_background=)```                                       | takes plain messages while the user sits on the screen ```name``` |
| ```@module.match(predicate, priority=, role=, is_background=)```                         | takes messages matching ```predicate(text)```                     |
| ```@module.job(interval=, name=, is_aligned=)```                                         | runs every ```interval``` seconds in its own thread               |
| ```@module.action("name", parameters=, optional=, description=, role=, is_confirmed=)``` | lets the assistant do ```name``` for the user                     |
| ```@module.context()```                                                                  | tells the assistant what the module knows about the user          |
| ```@module.expose("name", is_writing=)```                                                | lets the modules that require or use this one read ```name```     |
| ```@module.form("name", questions, parent=, title=)```                                   | asks its questions one by one and passes the answers on           |

- ```role``` defaults to ```Role.GUEST```.
- There are three ranks: ```Role.BANNED```, ```Role.GUEST``` and ```Role.ADMIN```. Everyone new is a guest.
- A module with ```is_guarded=True``` needs access as a whole - every command, button, answer and its settings. An admin
  gives one person one module, or puts the module on the default list for everybody. Without access the person is
  offered to ask for it, and the admins get the request with Grant and Refuse buttons. A ```role=Role.ADMIN``` handler
  still needs the rank on top.
- A message that is not text - a photo, a voice message, a location and so on - skips commands and screens, and goes
  only to matchers naming its kind in ```media```, as in ```media=("photo", "voice")```, without the predicate. When
  nobody takes it, the person hears that the Bot does not understand.
- A matcher of a guarded module stays silent towards people without access, and the message goes on as if the module
  were not there. Only a command answers them with the offer to ask, so a module catching plain messages does not pester
  anyone.
- A command for admins only is hidden: it stays out of the Telegram command menu and out of the help screen, because
  both are the same for everybody.
- ```is_background=True``` puts the handler on its own thread - use it for anything that takes time, like downloading or
  calling a remote API.
- ```is_aligned=True``` on a job makes it wait until the clock reaches the next whole interval, so a check every 60
  seconds lands on the minute instead of drifting from whenever the Bot started.
- Matchers are sorted by priority, highest first, then by module name and declaration order, so the outcome does not
  depend on the order modules are loaded.

## 🖥️ Screens

A view with a name is a screen. Each one says where it sits with ```parent```, and what to call it in the breadcrumb
with ```title``` - a text key, like everything else the user reads. The screens of a module make a tree, and the core
walks it: the breadcrumb, the back button and where back lands all come from the tree, never from what the user pressed
before.

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

A handler returns what should appear:

- ```str``` or a ```View``` without a name - a single message,
- ```View``` returned by a ```@module.view``` function - a screen,
- ```None``` - the handler already did everything it wanted.

A ```View``` with ```photo=``` - the bytes of a picture, such as a chart drawn into memory - is sent as that picture
with the text under it. As a screen it takes the place of the last one like any other screen, and its buttons stay
under the picture. The text of a picture can be at most 1024 characters, so the core keeps the heading, the first line
and the latest lines, and puts ```…``` where the rest was.

One message at a time carries the screen. A button press rewrites that message where it is, so moving around a module
adds nothing to the chat. A typed message - a command, an answer to a question - is different: the user has written
something, so the screen is taken away and written again below what they said, and it stays the last thing in the chat.
Running the same command twice reopens its screen at the bottom instead of leaving two of them around.

Use ```Button.command(text, "help")``` for a button that runs a command - the core routes it, so one module never needs
to know another module's actions.

> Back, Menu and Close belong to the core. It draws them by depth, rebuilds the parent from the tree and remembers the
> argument each screen was last opened with, so going back to page 3 of a list returns to page 3. Modules write no
> navigation code.

An answer the module cannot use is not a message of its own - ```ctx.retry``` asks the same screen again with the
problem written above the question:

```python
@module.state("set")
def take_content(ctx: Ctx) -> View:
    if not ctx.text.strip():
        return ctx.retry(ctx.t("set.empty"))
    return save(ctx)
```

### Forms

A few questions in a row are a form. The module lists them and gets every answer at once; the screens, the answers kept
between messages, the buttons and ```ctx.retry``` belong to the core, so every module asks the same way:

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

- A ```number``` takes a comma as well as a dot and a trailing ```%```, and must fit between ```low``` and ```high```.
  ```parse=``` swaps the check for the module's own: it gets the text and the answers so far, and gives back the value
  or ```None```, with ```problem=``` naming the text shown then. ```Problem("key", {'low': 1})``` names the exact
  problem instead.
- A ```weight``` and a ```height``` are typed in the units the user picked in Settings > About me - kilograms or
  pounds, centimetres or feet and inches - and always reach the module in kilograms and centimetres, ```low``` and
  ```high``` included. ```{unit}``` in the question names the unit, and ```ctx.profile.weight(kg)``` and
  ```ctx.profile.height(cm)``` show a value back the same way.
- A ```text``` is stripped and must be between ```low``` (at least 1) and ```high``` characters long.
- A ```choice``` is answered with buttons named ```<key>.<choice>```, a ```moment``` with Now, 30 min, 1 h and 2 h ago
  or a typed ```21:30```, ```21.30```, ```2026-10-30 21:30```, ```30.10.2026 21:30``` or ```30.10 21:30``` in the
  current year, never in the future and at most ```back``` hours ago - ```back=None``` lets it go back as far as the
  user wants. ```read_moment(text, now, is_future=)``` reads the same ways of writing it for a module's own checks.
- ```clear=``` adds a button, named by that text key, that answers with ```None``` - for an answer the user would
  rather not give. ```is_needed=``` gets the answers so far and skips the question when it says ```False```, so a
  form asks about the last drink only when there was more than one.
- The question itself is the text ```ask.<key>```, or ```text=```. It and the ```problem``` may name any answer given
  so far, or any value passed in ```known```, as a placeholder - ```Write your weight in {unit}```.
- ```known``` answers are not asked. ```offered``` ones come from what the user saved: the core asks once whether to use
  them, without showing them, and drops the empty ones, the ones no question would accept and the whole offer when
  nothing in it answers a question. Pass only what is fresh enough to use without a second look.
- Data from different places is offered apart: ```offered=[("offer.body", body), ("offer.drinks", drinks)]``` asks
  about each group with its own text, so the user can take one and type the other.
- ```Answers``` holds the ```values```, which keys were ```typed``` and which belong to a ```declined``` group.
  ```answers.new(keys)``` is what the user typed for themself - what may be offered for saving.
- A form belongs to the screen it was opened from: Back on its first question returns there. Leaving it - with a
  command, another screen or ```ctx.close_screen()``` - forgets the answers given so far, so nothing half typed waits
  for a later message.

A module with options of its own declares one settings screen. The Bot lists it under Modules in ```/settings```, a page
at a time, and the screen sits under that list: the heading reads, for example,
```⚙️ Settings > 🧩 Modules > 📥 Downloader```, and Back returns to the list. Opened with ```Button.settings``` from a
screen of the module itself, Back and Menu return to that module instead.
Screens deeper in the settings take ```parent="settings"```:

```python
@module.settings()
def settings(ctx: Ctx) -> View:
    return View(text=ctx.t("settings.text"), buttons=[Button(ctx.t("settings.format"), "format")])
```

## 🤖 Assistant

A module can let the assistant - the ```llm``` module - work in it for the person talking to it. An action is a function
the language model may call, with arguments it fills in itself:

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

- An action runs with the ```Ctx``` of the person talking, like any handler. The model chooses the arguments only, never
  the person, so nothing it sends reaches anybody else's data.
- Arguments are ```str```, ```int```, ```float``` or ```bool```, and each one is required, unless it is named in
  ```optional=["date"]``` - then one the model leaves out comes as ```None```. The core turns ```"3"``` into ```3``` and
  refuses what does not fit before the module sees it.
- The module checks the values with the same functions its screens use. What ```ctx.retry``` shows on a screen,
  ```Outcome.refused``` gives to the model, which can then ask the person again. ```past_moment(text)``` reads a time
  the way a ```moment``` question does and gives it back as ISO, or ```None``` when it is wrong or still to come.
- A parameter naming a user - ```user```, ```user_id```, ```other_user``` - is refused when the module loads, so an
  action can never be pointed at somebody else.
- ```Outcome.done(result)``` is the answer - a short text, or a list or a dict of plain values for the model to read.
- ```Outcome.ask(question, then)``` says what would happen. With ```is_confirmed=True``` the person gets the question
  with ✅ and ❌ buttons. ✅ runs the action again from the start, so everything is checked once more, and only then calls
  ```then()```, whose text takes the place of the question. Without ```is_confirmed``` the core calls ```then()``` at
  once.
- An action is offered only to people who may use its module, and with ```role=``` only to those with the rank. A module
  turned off, or one that did not load, offers nothing.
- The model knows an action as ```module_action```, like ```reminder_add```. What it reads about it are texts like any
  other: ```actions.add``` describes the action and ```parameters.content``` a parameter, shared by every action of the
  module. ```description=``` names another key for the action.

A module can also tell the assistant what it knows about the person - a few lines it may bring up on its own:

```python
@module.context()
def summary(ctx: Ctx) -> str:
    return "\n".join(escape(row['date'] + " - " + row['content']) for row in upcoming(ctx))
```

The summary is markup like every other text, so whatever the user wrote is escaped. The core turns it into plain text
and keeps five lines at most. In the assistant's settings the person decides which modules it may read and act in.

> Only a module with ```is_assistant=True``` in its manifest gets ```ctx.assistant```: ```modules()```, ```actions()```,
> ```act(module, action, arguments, is_confirmed=)``` and ```context(module)```, always for ```ctx.user```.

## 🎒 Context

Every handler takes one argument.

```python
ctx.t("key", name="value")  # this module's texts, in the user's language
ctx.t("core:yes_button")  # another namespace, named explicitly
ctx.user  # id, name, role, language, consent
ctx.text  # the incoming message text, or the caption of a photo, a video and so on
ctx.kind  # what came: "text", "photo", "voice", "location"... as Telegram names it
ctx.forwarded_from  # who wrote a forwarded message, if they let it show
ctx.arguments  # arguments from the callback data
ctx.state["step"] = "2"  # per user and module, kept in the database
ctx.nav  # where the user is, and what each screen of this module remembered
ctx.db  # this module's own tables
ctx.token("service_key")  # only the secrets declared in the manifest
ctx.has_token("service_key")  # whether a declared secret is set at all
ctx.setting("service_url")  # a declared entry of config.yaml, None when it is missing
ctx.has_module("bodytracker")  # whether a required or used module is loaded and the user may use it
ctx.ask("bodytracker", "latest")  # what that module exposes under "latest", None when has_module is False
ctx.profile  # sex, date of birth, age and units, shared by every module, all of it optional
ctx.set_profile(sex="female")  # changes the shared details, checking every value
ctx.form("body", known={}, offered={})  # starts a form: skips what is known, offers what is saved, in groups too
message_id = ctx.reply_live(text)  # a message the module can rewrite later, is_silent=True sends it quietly
ctx.edit(message_id, text)  # rewrites it, False when Telegram refuses
ctx.remove(message_id)  # deletes it, False when Telegram refuses
ctx.remove_buttons(message_id)  # takes its buttons away and keeps the text, False when Telegram refuses
ctx.log("Reminder set")  # "Reminder set: First (1)."
ctx.retry(problem)  # the same screen again, with the problem above the question
ctx.close_screen()  # closes the screen the user acted on, ending the flow
ctx.send_file(path, "video")  # audio, document, photo, video or voice
ctx.send_album(pictures)  # pictures as albums of up to ten
ctx.file_limit  # the largest file Telegram lets a bot upload
ctx.download(file_id)  # the bytes of a file the person sent, None when Telegram refuses
ctx.download_limit  # the largest file Telegram lets a bot download
with ctx.workspace() as path:  # a temporary directory, removed even after a failure
    ...
```

Internal modules get more:

```python
ctx.users, ctx.settings, ctx.registry, ctx.config  # the core repositories and the configuration
ctx.access, ctx.can_use("reminder")  # who may use which module
ctx.version  # the Bot version, read from git on start
ctx.languages  # every language the Bot supports, as (code, label) pairs
ctx.use_language("pl")  # changes the user's language, this context included
ctx.language_of(user_id)  # another user's language
ctx.text_for(user_id, "key")  # a text in another user's language
ctx.notify(user_id, view)  # writes to another user as a notification
```

> External modules do not have these attributes at all.

A background job handler takes a ```JobCtx``` instead: ```db```, ```t(key, language)```, ```language_of(user_id)```,
```send(user_id, view)``` and ```log```.

## 🤝 Working with other modules

```requires``` makes a module part of another one: without it the module is skipped. ```uses``` is the loose kind - the
module loads either way and checks at runtime whether the other one is there. A module shares what it wants others to
read through a function it exposes:

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

- The exposed function runs as the module that exposes it: it gets its own ```ctx``` for the same user, so it reads
  its own tables, and whatever came after the name in ```ctx.ask``` as further arguments.
- ```ctx.has_module``` and ```ctx.ask``` answer ```False``` and ```None``` when the other module is turned off, failed
  to load, or is guarded and the user has no access to it. ```ctx.ask``` answers ```None``` as well when the exposed
  function fails - the error goes to the log and the asking module carries on. Naming a module that is neither in
  ```requires``` nor in ```uses``` raises ```PermissionError```, and asking for something it does not expose raises
  ```LookupError```.
- Modules are installed after the ones they require or use. A module whose required module failed to install is
  skipped as well; one whose used module failed simply goes on without it.
- Two modules may use each other. A module cannot use itself, nor both require and use the same module.
- An exposed function may take arguments and change the data of its module, which is how a result offers to save
  what the user typed into a tracker. Such a function is declared with ```is_writing=True```, and the core runs it only
  after the user pressed a button, or the assistant's action was confirmed - asked any other way it raises
  ```PermissionError```.
- What describes the user and not one module - sex, date of birth, units - lives in ```ctx.profile```, not in a module
  of its own, so every module reads and writes the same details.
- A module may import from the modules it uses, but such an import fails when the other directory is gone. Prefer
  ```ctx.ask```, and import only what is safe to miss, inside the function that needs it.

## 🌐 Texts

Every module has its own namespace, so ```key1``` in one module and ```key1``` in another are two different texts.
Nested YAML flattens with dots:

```yaml
menu:
  title: Reminders     # menu.title
```

Texts hold words only. An emoji that opens or closes a text belongs in the manifest's ```icons``` and ```endings```, so
it is written once instead of once per language, and a translation cannot drift from it. The contract refuses an icon or
ending for a key that has no text. An emoji in the middle of a sentence stays in the text.

Every module needs a ```name``` and a ```description``` key - ```/help``` and ```/features``` list modules as
```/command - Name - Description```.

The languages the Bot supports are the files in ```core/locales```. A module ships one file per language, no more and no
less, and ```en.yaml``` is the fallback for every other language. Each language names itself in its own file under
```language_label```, so a new language is added in one place.

> A missing key is not an error. The user sees ```reminder:menu.title```.

### Formatting

A text is one bare line of words, so translating it takes nothing but words. The contract refuses a text in quotes, a
text broken into lines and a text with tags or Markdown. Everything else is the code's job - it puts lines together,
adds the colon that introduces a value and decides how each part looks:

```yaml
menu: Reminders you have set
pick:
  text: Pick the reminder you want to manage.
  page: Page {page} of {pages}, {total} in total
labels:
  content: Content
  date: Date
```

A message put together from several texts gets a group of its own, so the parts that belong together stay together. The
main sentence is ```text```, a heading shown in bold is ```title```, and every other part is named after what it adds -
```hint```, ```page```. Names of fields shown as ```Label: value``` live under ```labels```. A value that sits inside a
sentence stays a placeholder, ```This is {name}!```, never a sentence cut in two around it - another language may need
the words in a different order.

```python
from core.api import bold, escape, italic, labelled

labelled(ctx.t("menu"), len(rows))  # "Reminders you have set: <i>3</i>"
ctx.t("pick.text") + "\n" + ctx.t("pick.page", page=italic(page), pages=italic(pages), total=italic(total))
ctx.t("done", role=italic(role))  # "The rank has been changed to {role}" with the role in italics
Button(escape(row['content']), "one", row['id'])  # anything the user wrote, turned into safe text
```

> A text never ends with a colon or contains one followed by a space, and ```yes```, ```no```, ```on``` and ```off```
> alone are words YAML reads as true and false. Where a sentence needs them, it is worded differently or split.

Messages go out as HTML. Whatever reaches ```ctx.t``` as a value is escaped on the way in, so a name like
```<Eve> & co``` or a username like ```john_doe``` cannot break a message. ```bold``` and ```italic``` escape what they
wrap too; ```escape``` is for the rest of what a module glues together by hand. A text from ```ctx.t``` is markup
already and is never escaped twice. Buttons and the Telegram command menu take plain text, and the core strips the
markup from them itself.

## 🗄️ Tables

A module owns tables prefixed with ```module_<name>_```. Put them in ```schema.sql``` next to ```module.py``` and the
loader creates them on start:

```sql
CREATE TABLE IF NOT EXISTS module_reminder_reminders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date TEXT NOT NULL
);
```

> The foreign key is worth having: deleting a user then clears the module's rows as well, which is exactly what deleting
> data on request has to do.

There is no schema versioning. Changing a table that already exists somewhere is a manual migration of that instance.

## 🧪 Tests

A module needs no test setup of its own. Two fixtures are handed to every test:

```python
from core.testing import make_message


def test_the_menu_opens(app, bot):
    app.router.handle_message(make_message("/reminder"))
    assert bot.last.text.startswith("*🔔 Reminders:*")
```

- ```app``` - a Bot with every internal module loaded, an empty database and a fake Telegram,
- ```bot``` - what the Bot sent, edited and deleted during the test.

In tests ```ctx.ask``` raises what the exposed function raised instead of only logging it, so a broken call between
modules fails the test.

> ```core.testing``` also provides ```make_message```, ```make_callback```, ```make_storage```, ```FakeBot``` and
> ```not_none``` for tests that need to build their own pieces. Tests need no network and no database file.

## 🔌 Turning modules off

```config/modules.yaml``` lists only what is to be turned off:

```yaml
youtube: false
```

- No file means everything is on.
- A module missing from the file is on.
- Internal modules cannot be turned off.

## ✅ Contract

```core/contract.py``` checks every module with the following set of tests:

- the manifest name matches the directory, nothing requires or uses itself, and no module is both required and used,
- there is one language file per language the Bot supports, each with the same keys as ```en.yaml```, including
  ```name```, ```description``` and a description key for every command,
- every action has a text describing it and a text for each of its parameters,
- every text is one bare line, with no quotes, line breaks, tags or Markdown,
- callback names leave room for arguments within Telegram's 64 byte limit,
- ```schema.sql``` creates objects carrying the module prefix only,
- an external module imports only ```core.api``` and ```core.testing``` from the core, and from other modules only those
  listed in ```requires``` or ```uses```,
- every package the module imports outside its ```tests``` is named in its own ```requirements.txt```,
- the module has a ```tests``` directory.
