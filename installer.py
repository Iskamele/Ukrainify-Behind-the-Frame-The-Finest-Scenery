# -*- coding: utf-8 -*-
"""Entry point for the packaged installer (PyInstaller --onefile).

Finds the game, patches it, checks the result, waits for a keypress.
"""
import os, re, sys, ctypes

if sys.platform == 'win32':
    try:
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import apply as A
import verify as V

TAIL = os.path.join('steamapps', 'common', 'Behind the Frame - The Finest Scenery',
                    'BehindTheFrame_PC_Steam', 'Behind the Frame_Data')


def steam_libraries():
    roots = []
    for base in (r'C:\Program Files (x86)\Steam', r'C:\Program Files\Steam',
                 os.path.expandvars(r'%ProgramFiles(x86)%\Steam')):
        if base and os.path.isdir(base):
            roots.append(base)
    for base in list(roots):
        vdf = os.path.join(base, 'steamapps', 'libraryfolders.vdf')
        if os.path.isfile(vdf):
            try:
                txt = open(vdf, encoding='utf-8', errors='ignore').read()
            except OSError:
                continue
            for m in re.finditer(r'"path"\s+"([^"]+)"', txt):
                roots.append(m.group(1).replace('\\\\', '\\'))
    seen, out = set(), []
    for r in roots:
        if r.lower() not in seen:
            seen.add(r.lower())
            out.append(r)
    return out


def find_game():
    for root in steam_libraries():
        p = os.path.join(root, TAIL)
        if os.path.isfile(os.path.join(p, 'resources.assets')):
            return p
    return None


def ask(prompt):
    try:
        return input(prompt).strip().lower()
    except EOFError:
        return ''


def main():
    print()
    print('  Behind the Frame — українська локалізація')
    print('  ' + '=' * 42)
    print()

    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path:
        path = path.strip('"')
        if os.path.basename(path).lower() != 'behind the frame_data':
            cand = os.path.join(path, 'BehindTheFrame_PC_Steam', 'Behind the Frame_Data')
            if os.path.isfile(os.path.join(cand, 'resources.assets')):
                path = cand
    if not path or not os.path.isfile(os.path.join(path, 'resources.assets')):
        print('  Шукаю гру...')
        path = find_game()

    if not path:
        print()
        print('  Гру не знайдено.')
        print()
        print('  Перетягніть на цей файл папку "Behind the Frame_Data"')
        print('  (вона всередині папки гри, у BehindTheFrame_PC_Steam),')
        print('  або вкажіть шлях у командному рядку.')
        print()
        ask('  Enter — вийти ')
        return 1

    print(f'  Гра: {path}')
    print()
    print('  Буде змінено resources.assets і 1 МБ усередині resources.assets.resS.')
    print('  Поряд зберуться копії .orig — щоб можна було відкотитись.')
    print('  Збереження не чіпаються (вони в AppData\\LocalLow).')
    print()
    if ask('  Встановити? [y/N] ') not in ('y', 'yes', 'т', 'так', 'д', 'да'):
        print('  Скасовано.')
        return 0

    print()
    try:
        g = A.Game(path)
    except SystemExit as e:
        print(f'  {e}')
        ask('  Enter — вийти ')
        return 1

    made = A.backup(g)
    print('  Копії:', ', '.join(made) if made else 'вже існують, лишаю як є')
    print()
    print('  Встановлення:')
    try:
        for name, fn in A.STAGES:
            fn(g)
        size = g.save()
    except Exception as e:
        print()
        print(f'  ПОМИЛКА: {type(e).__name__}: {e}')
        print('  Гру не змінено повністю. Відновіть файли через Steam:')
        print('  Властивості > Встановлені файли > Перевірити цілісність.')
        print()
        ask('  Enter — вийти ')
        return 1
    print(f'  Записано resources.assets ({size / 1e6:.1f} МБ)')

    print()
    print('  Перевірка:')
    try:
        g2 = A.Game(path)
        good = V.verify(g2)
    except Exception as e:
        print(f'  перевірку не вдалося виконати: {e}')
        good = None

    print()
    if good:
        print('  Готово. Запустіть гру та оберіть мову «Українська».')
    elif good is None:
        print('  Встановлено, але перевірка не запустилась. Перевірте гру вручну.')
    else:
        print('  Перевірка знайшла розбіжності — дивіться список вище.')
    print()
    ask('  Enter — вийти ')
    return 0 if good is not False else 1


if __name__ == '__main__':
    sys.exit(main())
