# Deadlock Solomon Piece Reminder

Страница мода: https://gamebanana.com/mods/726023

Мод для Deadlock (Соломон, внутреннее имя `chessmaster`). Чисто визуальный, геймплей не трогает:

1. **Напоминание.** Если выставлена фигура (1-я способность - слон, 4-я - ферзь, конь тоже), а способность
   висит в режиме «нажми ещё раз» дольше 15 секунд без изменений, её иконка в HUD мигает красным. Фигуру убрал,
   переставил, пошёл кулдаун - отсчёт сбрасывается, мигание гаснет.
Только напоминание: модели и материалы фигур мод не трогает. Неоновая разметка на полу - отдельный мод
`DeadlockSolomonNeonSquares` рядом с этой папкой.

## Как сделано

- **Напоминание**: подменяется `panorama/layout/hud_ability_icon.xml` (родная разметка иконки + подключение
  `hud/solomon_reminder.css` и `hud/solomon_reminder.js`). Скрипт живёт внутри каждой иконки, раз в полсекунды
  смотрит на её классы состояния (`.active` / `.toggled_on` / `.is_trigger`, без `.cooling_down`) и через
  `DELAY` секунд непрерывного состояния вешает класс `solomon_overdue`, по которому CSS мигает. В варианте
  `solomon` реагируют только иконки с классами `subcast_chessmaster_*` (слон/конь/ферзь Соломона).
  Первая версия была на CSS `animation-delay` - Panorama в Deadlock его игнорирует, мигало сразу.
- Файлы ставятся в `pak03_dir.vpk`: три файла HUD, больше ничего.

## Что нужно

- Deadlock (путь по умолчанию `D:\SteamLibrary\steamapps\common\Deadlock`, иначе переменная `DEADLOCK`).
- Python 3.12+ (пакет `lz4` желателен: `pip install lz4`; без него работает свой медленный LZ4).
- [Source 2 Viewer CLI](https://github.com/ValveResourceFormat/ValveResourceFormat/releases) - путь `S2V_CLI`
  (по умолчанию берётся из проекта DeadlockNeonCrate, `tools/cli/Source2Viewer-CLI.exe`).
- [Reduced CSDK 12](https://deadlockmodding.pages.dev/modding-tools/csdk-12) - путь `CSDK` в `build.bat`
  и `solomon_reminder.py`. Без него тоже соберётся: `python solomon_reminder.py pack --raw` подменяет текст
  прямо в оригинальном `vcss_c`.

## Сборка и установка

```bat
build.bat
```

Сделает всё сразу: `stage` -> компиляция -> `pack` -> `install` (копирует `build\solomon\pak03_dir.vpk`
в `Deadlock\game\citadel\addons\`). Потом перезапустить игру.

- `build\SolomonReminder_solomon_15s.zip` - для Deadlock Mod Manager (Add Local Mod).
- `build\SolomonReminder_universal_15s.zip` - вариант без привязки к Соломону (мигает любая способность
  любого героя, висящая активной дольше 15 с): `python solomon_reminder.py install universal`.

Номер `pak03` выбран потому, что `pak01` (Neon Crates) и `pak02` (Buff Timer) уже заняты. Игра грузит
`pakNN_dir.vpk` по порядку; Deadlock Mod Manager при отключении мода переименовывает файл в `<id>_pakNN_dir.vpk`,
и такие файлы игра не видит.

## Настройка

- `solomon_reminder.py`: `DELAY` - через сколько секунд мигать (15), `BLINK` - период мигания (0.5 с).
- `hud/solomon_reminder.js`: списки классов состояний (`ON_STATES`) и иконок Соломона (`SOLOMON_CLASSES`).
- `hud/solomon_reminder.css`: цвета и амплитуда мигания.

После правок снова `build.bat`.

## Конфликты

Любой мод, который тоже подменяет `panorama/styles/hud_ability_icon.vcss_c` или `hud_abilities.vcss_c`
(например, крупные HUD-моды вроде 650634 в твоём Mod Manager).
Выигрывает меньший номер pak.

## Что проверить в игре (я не мог)

- Напоминание: поставить слона или ферзя и не трогать 15 с - иконка 1/4 должна замигать красным; убрать фигуру -
  погаснуть. Сразу после установки мигать не должно.

## Восстановление с нуля

В git лежит только исходный код. Папки `extract/` и `build/` в репозиторий не кладутся: это файлы игры (ресурсы Valve) и то, что
из них собрано. Всё это пересоздаётся сборкой.

1. Скачать проект:

```bash
git clone https://github.com/gizmenono4ek/deadlock-solomon-reminder.git DeadlockSolomonReminder
```

2. Поставить инструменты, если их нет на компьютере:

- Deadlock из Steam. Путь по умолчанию `D:\SteamLibrary\steamapps\common\Deadlock`, иначе переменная `DEADLOCK`
  (где путь зашит в скрипт, поправить в начале скрипта).
- Python 3.12+ и пакеты: `pip install pillow lz4`.
- [Reduced CSDK 12](https://deadlockmodding.pages.dev/modding-tools/csdk-12): распаковать в
  `C:\Users\Alexd\Downloads\Reduced_CSDK_12\Reduced_CSDK_12` (так прописано в скриптах) или поправить путь `CSDK`.
- Source 2 Viewer CLI: [релизы ValveResourceFormat](https://github.com/ValveResourceFormat/ValveResourceFormat/releases),
  архив `cli-windows-x64.zip`, распаковать так, чтобы был
  `C:\Users\Alexd\Documents\DeadlockNeonCrate\tools\cli\Source2Viewer-CLI.exe`
  (папка `tools` у NeonCrate в git не входит, её тоже придётся скачать заново).

3. Пересобрать:

```bat
build.bat
```

Подробности и варианты (`install universal`, `pack --raw` без CSDK) — в разделе «Сборка и установка» выше.
