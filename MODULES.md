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

> The directory name, the manifest name and the table prefix must all agree. The loader refuses a module whose
> ```module.py``` declares a different name than its directory.

## ⚙️ Manifest

```python
module = Module(
    name="reminder",  # lowercase letters, digits, underscores
    requires=["downloader"],  # other modules that must be loaded first
    tokens=["spotify_id"])  # the only secrets this module can read
```

> A module that needs a pip package ships its own ```requirements.txt``` next to ```module.py```, and the contract
> refuses a module that imports something it did not declare. The name of the package counts, not the name of the
> import, so ```bs4``` is declared as ```beautifulsoup4```. When the package is missing, the module is skipped with a
> line in the log and the Bot starts without it.

## 🧩 Declarations

| Decorator                                                          | What it does                                                      |
|--------------------------------------------------------------------|-------------------------------------------------------------------|
| ```@module.command("name", role=, description=, is_background=)``` | registers ```/name``` and adds it to the Telegram command menu    |
| ```@module.callback("action", role=, is_background=)```            | handles the button ```module:action:arguments```                  |
| ```@module.view("name")```                                         | builds a screen the core can rebuild when going back              |
| ```@module.state("name", role=, is_background=)```                 | takes plain messages while the user sits on the screen ```name``` |
| ```@module.match(predicate, priority=, role=, is_background=)```   | takes messages matching ```predicate(text)```                     |
| ```@module.job(interval=, name=)```                                | runs every ```interval``` seconds in its own thread               |

- ```role``` defaults to ```Role.GUEST```.
- ```is_background=True``` puts the handler on its own thread - use it for anything that takes time, like downloading or
  calling a remote API.
- Matchers are sorted by priority, highest first, then by module name and declaration order, so the outcome does not
  depend on the order modules are loaded.

## 🖥️ Screens

A view with a name is a screen: it goes on the user's navigation stack, gets a back button and can be rebuilt when the
user presses it.

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

A handler returns what should appear:

- ```str``` or a ```View``` without a name - a single message,
- ```View``` returned by a ```@module.view``` function - a screen,
- ```None``` - the handler already did everything it wanted.

A command starts a fresh navigation, a callback goes one level deeper. Running the same command twice therefore reopens
its screen instead of stacking it. Use ```Button.command(text, "help")``` for a button that runs a command - the core
routes it, so one module never needs to know another module's actions.

> The back button belongs to the core: it deletes the current screen, pops it off the stack and rebuilds the parent.
> Modules write no navigation code.

## 🎒 Context

Every handler takes one argument.

```python
ctx.t("key", name="value")  # this module's texts, in the user's language
ctx.t("core:yes_button")  # another namespace, named explicitly
ctx.user  # id, name, role, language, consent
ctx.text  # the incoming message text
ctx.forwarded_from  # who wrote a forwarded message, if they let it show
ctx.arguments  # arguments from the callback data
ctx.state["step"] = "2"  # per user and module, kept in the database
ctx.nav  # the navigation stack, scoped to this module
ctx.db  # this module's own tables
ctx.token("spotify_id")  # only the secrets declared in the manifest
ctx.log("Reminder set")  # "Reminder set: First (1)."
ctx.close_screen()  # closes the screen the user acted on
ctx.send_file(path, "video")  # audio, document, photo, video or voice
ctx.file_limit  # the largest file Telegram lets a bot upload
with ctx.workspace() as path:  # a temporary directory, removed even after a failure
    ...
```

Internal modules get more:

```python
ctx.users, ctx.settings, ctx.registry, ctx.config  # the core repositories and the configuration
ctx.version  # the Bot version, read from git on start
ctx.languages  # every language the Bot supports, as (code, label) pairs
ctx.use_language("pl")  # changes the user's language, this context included
ctx.language_of(user_id)  # another user's language
ctx.text_for(user_id, "key")  # a text in another user's language
ctx.notify(user_id, view)  # writes to another user, respecting their notification setting
```

> External modules do not have these attributes at all.

A background job handler takes a ```JobCtx``` instead: ```db```, ```t(key, language)```, ```language_of(user_id)```,
```send(user_id, view)``` and ```log```.

## 🌐 Texts

Every module has its own namespace, so ```key1``` in one module and ```key1``` in another are two different texts.
Nested YAML flattens with dots:

```yaml
menu:
  title: Reminders     # menu.title
```

Every module needs a ```name``` and a ```description``` key - ```/help``` and ```/features``` list modules as
```/command - Name - Description```.

The languages the Bot supports are the files in ```core/locales```. A module ships one file per language, no more and no
less, and ```en.yaml``` is the fallback for every other language. Each language names itself in its own file under
```language_label```, so a new language is added in one place.

> A missing key is not an error. The user sees ```reminder:menu.title```.

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

- the manifest name matches the directory and nothing requires itself,
- there is one language file per language the Bot supports, each with the same keys as ```en.yaml```, including
  ```name```, ```description``` and a description key for every command,
- callback names leave room for arguments within Telegram's 64 byte limit,
- ```schema.sql``` creates objects carrying the module prefix only,
- an external module imports only ```core.api``` and ```core.testing``` from the core, and from other modules only those
  listed in ```requires```,
- every package the module imports outside its ```tests``` is named in its own ```requirements.txt```,
- the module has a ```tests``` directory.
