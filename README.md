# Deadlock Solomon Piece Reminder

Страница мода: https://gamebanana.com/mods/726023

Мод для Deadlock (Соломон, внутреннее имя `chessmaster`). Чисто визуальный, геймплей не трогает:

1. **Напоминание.** Если выставлена фигура (1-я способность - слон, 4-я - ферзь, конь тоже), а способность
   висит в режиме «нажми ещё раз» дольше 30 секунд без изменений, её иконка в HUD мигает красным. Фигуру убрал,
   переставил, пошёл кулдаун - отсчёт сбрасывается, мигание гаснет.
3. **Неоновая разметка на полу.** Клетки вокруг слона (и предупреждающие клетки ферзя) стали яркими:
   светлая клетка - толстый золотой неоновый контур с гало, тёмная - тёмная заливка с серой неоновой кромкой.
   `ground_neon.py`: свои текстуры из родных масок, свои материалы декалей (`projected_decals.vfx`,
   `g_flSelfIllumScale` константой вместо тусклого `$SELFILLUM`), цвета в партиклах.
2. **Фиолетовый ферзь.** Модель ферзя перекрашена через материал: обычные фигуры (слон, конь, ладья) родного
   цвета, ферзь фиолетовый, чтобы при перестановке не путаться. Эффекты/партиклы не тронуты.

## Как сделано

- **Напоминание**: подменяется `panorama/layout/hud_ability_icon.xml` (родная разметка иконки + подключение
  `hud/solomon_reminder.css` и `hud/solomon_reminder.js`). Скрипт живёт внутри каждой иконки, раз в полсекунды
  смотрит на её классы состояния (`.active` / `.toggled_on` / `.is_trigger`, без `.cooling_down`) и через
  `DELAY` секунд непрерывного состояния вешает класс `solomon_overdue`, по которому CSS мигает. В варианте
  `solomon` реагируют только иконки с классами `subcast_chessmaster_*` (слон/конь/ферзь Соломона).
  Первая версия была на CSS `animation-delay` - Panorama в Deadlock его игнорирует, мигало сразу.
- **Ферзь**: `models/heroes_wip/chessmaster/materials/chessmaster_queen.vmat_c` (pbr.vfx) правится бинарно
  (`tools/kv3patch.py`, KV3 v5 + LZ4): `g_vColorTint1` (цвет модели, текстура серо-кремовая, тени остаются),
  `g_vSelfIllumTint1` (свечение, игра включает его в «тёмном» состоянии фигуры), `g_vSolidOutlineTint` (контур).
  Значения - `MATERIAL_OVERRIDES` в `piece_colors.py`. Там же остался задел на перекраску партиклов по
  способностям (`HUES`), сейчас выключен (`None`), потому что красит эффекты, а не фигуры.
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
- `piece_colors.py`: `MATERIAL_OVERRIDES` - цвет ферзя.

После правок снова `build.bat`.

## Конфликты

Любой мод, который тоже подменяет `panorama/styles/hud_ability_icon.vcss_c` или `hud_abilities.vcss_c`
(например, крупные HUD-моды вроде 650634 в твоём Mod Manager), а также моды на эффекты/скины Соломона.
Выигрывает меньший номер pak.

## Что проверить в игре (я не мог)

- Напоминание: поставить слона или ферзя и не трогать 30 с - иконка 1/4 должна замигать красным; убрать фигуру -
  погаснуть. Сразу после установки мигать не должно.
- Ферзь: сама фигура ферзя фиолетовая, остальные фигуры как были. Если оттенок не нравится - цифры в
  `MATERIAL_OVERRIDES`, потом `build.bat`.
