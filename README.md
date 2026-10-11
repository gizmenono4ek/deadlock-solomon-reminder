# Deadlock Solomon Piece Reminder

Страница мода: https://gamebanana.com/mods/726023

Мод для Deadlock (Соломон, внутреннее имя `chessmaster`). Чисто визуальный, геймплей не трогает:

1. **Напоминание.** Если выставлена фигура (1-я способность - слон, 4-я - ферзь, конь тоже), а способность
   висит в режиме «нажми ещё раз» дольше 30 секунд без изменений, её иконка в HUD мигает красным. Фигуру убрал,
   переставил, пошёл кулдаун - отсчёт сбрасывается, мигание гаснет.
Неоновая разметка на полу и цвета фигур (неон, золотой ферзь) вынесены в отдельный мод: папка
`DeadlockSolomonNeonSquares` рядом с этой. Reminder материалы фигур больше не трогает.

## Как сделано

- **Напоминание**: подменяется `panorama/layout/hud_ability_icon.xml` (родная разметка иконки + подключение
  `hud/solomon_reminder.css` и `hud/solomon_reminder.js`). Скрипт живёт внутри каждой иконки, раз в полсекунды
  смотрит на её классы состояния (`.active` / `.toggled_on` / `.is_trigger`, без `.cooling_down`) и через
  `DELAY` секунд непрерывного состояния вешает класс `solomon_overdue`, по которому CSS мигает. В варианте
  `solomon` реагируют только иконки с классами `subcast_chessmaster_*` (слон/конь/ферзь Соломона).
  Первая версия была на CSS `animation-delay` - Panorama в Deadlock его игнорирует, мигало сразу.
- **Цвета фигур** (бывший золотой ферзь / серебро) переехали в Solomon Neon Squares; `piece_colors.py` оставлен
  как задел (`MATERIAL_OVERRIDES` пуст, `HUES` выключен).
- Файлы ставятся в `pak03_dir.vpk`. Перекраска видна и у вражеского Соломона (та же модель).

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

- `build\SolomonReminder_solomon_30s.zip` - для Deadlock Mod Manager (Add Local Mod).
- `build\SolomonReminder_universal_30s.zip` - вариант без привязки к Соломону (мигает любая способность
  любого героя, висящая активной дольше 30 с): `python solomon_reminder.py install universal`.

Номер `pak03` выбран потому, что `pak01` (Neon Crates) и `pak02` (Buff Timer) уже заняты. Игра грузит
`pakNN_dir.vpk` по порядку; Deadlock Mod Manager при отключении мода переименовывает файл в `<id>_pakNN_dir.vpk`,
и такие файлы игра не видит.

## Настройка

- `solomon_reminder.py`: `DELAY` - через сколько секунд мигать (30), `BLINK` - период мигания (0.5 с).
- `hud/solomon_reminder.js`: списки классов состояний (`ON_STATES`) и иконок Соломона (`SOLOMON_CLASSES`).
- `hud/solomon_reminder.css`: цвета и амплитуда мигания.

После правок снова `build.bat`.

## Конфликты

Любой мод, который тоже подменяет `panorama/styles/hud_ability_icon.vcss_c` или `hud_abilities.vcss_c`
(например, крупные HUD-моды вроде 650634 в твоём Mod Manager), а также моды на эффекты/скины Соломона.
Выигрывает меньший номер pak.

## Что проверить в игре (я не мог)

- Напоминание: поставить слона или ферзя и не трогать 30 с - иконка 1/4 должна замигать красным; убрать фигуру -
  погаснуть. Сразу после установки мигать не должно.
