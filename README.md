# Behind the Frame: The Finest Scenery — українська локалізація

Повний неофіційний переклад українською. Не пов'язаний зі студією Silver Lining Studio.

Steam guide: https://steamcommunity.com/sharedfiles/filedetails/?id=3801864198

![версія](https://img.shields.io/badge/гра-Steam-blue) ![статус](https://img.shields.io/badge/переклад-100%25-brightgreen)

<img width="1920" height="1080" alt="20260915011211_1" src="https://github.com/user-attachments/assets/83370812-2c39-44db-a4fb-5ca17a1cb154" />

<img width="1920" height="1080" alt="20260915010336_1" src="https://github.com/user-attachments/assets/9e183a43-798d-4593-8a59-96deb2a67ad0" />

## Встановлення

Завантажте `BehindTheFrame-UA-Install.exe` зі сторінки [Releases](../../releases), закрийте гру й запустіть інсталятор. Гра знаходиться сама; якщо ні — перетягніть на нього папку `Behind the Frame_Data`.

У налаштуваннях гри оберіть **Українська**.

## Що зроблено

| | |
|---|---|
| Текст | 703 репліки: сюжет, меню, підказки, описи предметів |
| Шрифт | додано `і ї є ґ І Ї Є Ґ`, апостроф, багатокрапку, крапку з комою, тире |
| Намальований текст | 67 зображень: титульний екран, резюме, щоденник, записки, катсцени |

Переклад робився з англійського оригіналу. Російська версія використовувалась лише як орієнтир щодо довжини рядків — і в кількох місцях вона розходиться з оригіналом за змістом, там я йшов за англійською.

## Чому слот російської

Список мов вкомпільований у `GameAssembly.dll` — додати одинадцятий пункт без патчу нативного коду неможливо. Російський слот уже прив'язаний до кириличного шрифту, тому переклад займає саме його. У перемикачі мов пункт підписаний «Українська».

## Відкат

Інсталятор зберігає `resources.assets.orig` і `resources.assets.resS.orig` поряд із файлами гри — поверніть їх на місце, прибравши `.orig`.

Або через Steam: **Властивості → Встановлені файли → Перевірити цілісність**.

Збереження в папці гри не зберігаються, тому не постраждають за жодного сценарію.

## Відомі обмеження

- Оновлення гри та перевірка цілісності файлів у Steam повертають оригінал — просто запустіть інсталятор знову
- Антивірус може лаятись на `.exe`: це типове хибне спрацювання на PyInstaller. SHA-256 у `SHA256.txt`, вихідний код тут
- Перевірено на версії зі Steam станом на вересень 2026. На іншій версії інсталятор зупиниться з повідомленням, а не зіпсує файли

## Як це влаштовано

Інсталятор розпаковує та змінює вашу копію гри. Окрім перекладу й шрифту, він містить 67 зображень: ілюстрації гри з українськими написами замість оригінальних; самі ілюстрації належать студії. Вісім етапів за один прохід:

1. **font** — перезапечений атлас шрифту `MPLUSRounded1c`
2. **text** — 703 рядки у TextAsset `Language - Russian`
3. **label** — підпис мови в перемикачі
4. **title** — напис на титульному екрані
5. **computer** — дві сторінки резюме
6. **resume** — 36 слів-зображень: перепаковані в атлас і переверстані
7. **journal** — 16 рукописних нотаток
8. **cutscenes** — 12 реплік персонажів

Після запису інсталятор сам перевіряє результат: кількість гліфів, повноту тексту, відповідність кожного зображення вихідному файлу.

### Вихідний код

Переклад і графіка до репозиторію не входять (див. [LICENSE](LICENSE)), тож зібрати інсталятор лише з цих файлів не вийде. Код відкритий для ознайомлення — і для тих, хто робить щось подібне для іншої гри.

### Три технічні пастки

Якщо надумаєте робити щось подібне для іншої гри на Unity — ось те, на чому я втратив найбільше часу:

**Спрайт в атласі бере пікселі зі сторінки атласа, а не з власної текстури того самого імені.** Перемалювати окрему текстуру й чекати результату — марно, гра її не читає.

**Текст у головоломці — це UI-елементи.** Розмір і позицію задають `m_SizeDelta` та `m_AnchoredPosition` у `RectTransform`. Якщо оновити лише спрайт, нове зображення розтягнеться в стару рамку.

**Більшість спрайтів із текстом мають обрізаний `textureRect` і тісну сітку**, обведену по контуру старих літер. Усе, що виходить за той силует, просто не малюється.

## Ліцензії

Код — MIT. Переклад і перемальовані написи — усі права захищено: інсталятор можна завантажити з [Releases](../../releases) і запустити на власній копії гри; розміщення деінде (сайти, лаунчери, каталоги, збірки), використання як основи для інших перекладів і комерційне використання — лише з письмової згоди автора. Запит — через Issues. Ілюстрації під українськими написами належать Silver Lining Studio. Деталі — у [LICENSE](LICENSE).

Шрифт M PLUS Rounded 1c — [SIL Open Font License 1.1](data/font/OFL.txt).

Гра має бути придбана. Репозиторій не містить жодного файлу гри.

---

# Behind the Frame: The Finest Scenery — Ukrainian localisation

A complete unofficial Ukrainian translation. Not affiliated with Silver Lining Studio.

![game](https://img.shields.io/badge/game-Steam-blue) ![status](https://img.shields.io/badge/translation-100%25-brightgreen)

## Installing

Download `BehindTheFrame-UA-Install.exe` from [Releases](../../releases), close the game, run the installer. It finds the game on its own; if it does not, drag the `Behind the Frame_Data` folder onto it.

Then pick **Українська** in the game's settings.

## What is covered

| | |
|---|---|
| Text | 703 strings: story, menus, hints, item descriptions |
| Font | added `і ї є ґ І Ї Є Ґ`, apostrophe, ellipsis, semicolon, en dash |
| Drawn text | 67 images: title screen, résumé, journal, notes, cutscenes |

Translated from the English original. The Russian version was used only as a guide for line widths — and in a few places it diverges from the English in meaning, where I followed the English.

## Why the Russian slot

The language list is compiled into `GameAssembly.dll`, so an eleventh entry cannot be added without patching native code. The Russian slot is already wired to the Cyrillic font, so the translation takes that slot. In the language picker it reads "Українська".

## Uninstalling

The installer keeps `resources.assets.orig` and `resources.assets.resS.orig` next to the game files — rename them back by dropping `.orig`.

Or via Steam: **Properties → Installed Files → Verify integrity of game files**.

Saves live outside the game folder, so they survive either way.

## Known limitations

- Game updates and Steam's integrity check revert the files — just run the installer again
- Antivirus software may flag the `.exe`. This is a common false positive for PyInstaller builds: a Python interpreter is bundled inside and heuristics react to that. SHA-256 is in `SHA256.txt`, the source is here
- Verified against the Steam build as of September 2026. On a different version the installer stops with a message instead of damaging anything

## How it works

The installer unpacks and edits your own copy of the game. Besides the translation and the font, it carries 67 images: the game's artwork with Ukrainian lettering in place of the original; the artwork itself belongs to the studio. Eight stages in one pass:

1. **font** — rebaked `MPLUSRounded1c` glyph atlas
2. **text** — 703 strings into the `Language - Russian` TextAsset
3. **label** — the language picker entry
4. **title** — the title-screen lettering
5. **computer** — two full-page résumé images
6. **resume** — 36 word images, repacked into the atlas and re-laid-out
7. **journal** — 16 handwritten notes
8. **cutscenes** — 12 spoken lines

After writing, the installer verifies its own work: glyph count, text completeness, and every image against its source.

### Source code

The translation and artwork are not part of this repository (see [LICENSE](LICENSE)), so these files alone will not build the installer. The code is open to read — and for anyone doing something similar for another game.

### Three things that cost me the most time

If you are doing something similar for another Unity game:

**A sprite packed into an atlas takes its pixels from the atlas page, never from the standalone texture of the same name.** Repainting that texture does nothing — the engine never reads it.

**The puzzle text is made of UI Images.** Size and position come from `m_SizeDelta` and `m_AnchoredPosition` on the `RectTransform`. Update only the sprite and your new artwork gets stretched into the old box.

**Most text sprites ship with a cropped `textureRect` and a tight mesh** hugging the outline of the old lettering. Anything reaching outside that silhouette is silently clipped.

## Licences

Code: MIT. Translation and redrawn lettering: all rights reserved. Download the installer from [Releases](../../releases) and run it on your own copy; hosting it anywhere else (websites, launchers, catalogues, collections), using it as the basis for another translation, or any commercial use needs the author's written permission. Ask via Issues. The artwork under the Ukrainian lettering belongs to Silver Lining Studio. See [LICENSE](LICENSE).

M PLUS Rounded 1c font — [SIL Open Font License 1.1](data/font/OFL.txt).

You need to own the game. This repository contains no game files.
