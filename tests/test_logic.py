"""Сценарные тесты логики напоминания (зеркало функции step() из hud/solomon_reminder.js).

Panorama-рантайма вне игры нет, поэтому тестируем чистую логику на тех же правилах. Если меняешь step() в js,
поменяй и здесь. Запуск: python tests/test_logic.py
"""
import re
import sys
from pathlib import Path

DELAY = 15
GRACE = 3
POLL = 0.5


MAX_SIG_RESETS = 3


def step(st, armed, cooling, sig, now):
    if not armed and cooling:
        st["since"] = -1
    elif armed:
        if st["since"] < 0:
            st["since"] = now
            st["sig"] = sig
            st["sigResets"] = 0
        elif sig != st["sig"]:
            st["sig"] = sig
            if st["sigResets"] < MAX_SIG_RESETS:
                st["sigResets"] += 1
                st["since"] = now
        st["lastOn"] = now
    elif st["since"] >= 0 and now - st["lastOn"] > GRACE * 1000:
        st["since"] = -1
    recent = armed or now - st["lastOn"] <= GRACE * 1000
    return recent and st["since"] >= 0 and now - st["since"] >= DELAY * 1000


def run(timeline):
    """timeline: список (длительность с, armed, sig) или (длительность, armed, sig, cooling). -> [(t, blinking)]"""
    st = {"since": -1, "lastOn": -1, "sig": "", "sigResets": 0}
    t = 0.0
    out = []
    for item in timeline:
        dur, armed, sig = item[:3]
        cooling = item[3] if len(item) > 3 else False
        end = t + dur
        while t < end - 1e-9:
            out.append((round(t, 1), step(st, armed, cooling, sig if armed else st["sig"], int(t * 1000))))
            t += POLL
    return out


def blinking_between(res, a, b):
    return [bl for t, bl in res if a <= t < b]


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    return cond


def main():
    ok = True
    # 1. Поставил фигуру и не трогаешь: до 20 с тихо, после - мигает.
    r = run([(30, True, "A")])
    ok &= check("тихо первые 15 с", not any(blinking_between(r, 0, 15)))
    ok &= check("мигает после 15 с", all(blinking_between(r, 15.5, 30)))

    # 2. Убрал фигуру -> способность на кулдауне -> гаснет сразу.
    r = run([(25, True, "A"), (5, False, "", True)])
    ok &= check("гаснет сразу после уборки (кулдаун)", not any(blinking_between(r, 25, 30)))
    # 2b. Состояние пропало без кулдауна надолго (фигуру сняло как-то иначе) - гаснет не позже 3 с.
    r = run([(25, True, "A"), (10, False, "")])
    ok &= check("без кулдауна гаснет не позже 3 с", not any(blinking_between(r, 28.5, 35)))

    # 3. Тяжёлая атака / слайд / стан на 1 с: состояние пропало и вернулось - отсчёт не сброшен.
    r = run([(10, True, "A"), (1, False, ""), (15, True, "A")])
    ok &= check("пауза 1 с не сбрасывает отсчёт (мигает с 15.5 с)", all(blinking_between(r, 15.5, 26)))
    # 3b. Тяжёлая атака, когда уже мигает: мигание не прерывается.
    r = run([(20, True, "A"), (1.5, False, ""), (5, True, "A")])
    ok &= check("тяжёлая атака не прерывает мигание", all(blinking_between(r, 15.5, 26.5)))

    # 4. Пропало дольше 3 с - это уже новая фигура, отсчёт заново.
    r = run([(10, True, "A"), (4, False, ""), (25, True, "A")])
    ok &= check("пауза 4 с сбрасывает отсчёт", not any(blinking_between(r, 14, 29)))
    ok &= check("после новой постановки мигает через 15 с", all(blinking_between(r, 29.5, 39)))

    # 5. Взаимодействие с фигурой (перетащил): снимок классов изменился - отсчёт заново, мигание гаснет.
    r = run([(25, True, "A"), (10, True, "B")])
    ok &= check("мигало до перетаскивания", all(blinking_between(r, 15.5, 25)))
    ok &= check("после перетаскивания гаснет", not any(blinking_between(r, 25, 35)))
    r = run([(25, True, "A"), (25, True, "B")])
    ok &= check("и снова мигает через 15 с после перетаскивания", all(blinking_between(r, 40.5, 50)))

    # 5b. Слепок дёргается каждые 2 с (шум от игры): после 3 перезапусков его игнорируем, мигание всё равно приходит.
    r = run([(2, True, "A" + str(i % 2)) for i in range(25)])
    ok &= check("шумный слепок не глушит мигание навсегда", any(blinking_between(r, 0, 50)))
    ok &= check("шумный слепок: мигает не позже 25 с", all(blinking_between(r, 25, 50)))
    # 6. Не Соломон / способность не активна - никогда не мигает.
    r = run([(60, False, "")])
    ok &= check("без состояния не мигает", not any(bl for _, bl in r))

    # 7. Константы в js совпадают с тестом.
    js = (Path(__file__).parent.parent / "hud" / "solomon_reminder.js").read_text(encoding="utf-8")
    ok &= check("GRACE в js = тесту", f"GRACE_SECONDS = {GRACE};" in js)
    src = (Path(__file__).parent.parent / "solomon_reminder.py").read_text(encoding="utf-8")
    ok &= check("DELAY в solomon_reminder.py = тесту", re.search(rf"^DELAY = {DELAY}\b", src, re.M) is not None)
    # 8. Тело step() в js и здесь делает одно и то же: сверяем ключевые строки.
    ok &= check("js: сброс по смене снимка", "sig !== st.sig" in js)
    ok &= check("js: лимит перезапусков от слепка", f"MAX_SIG_RESETS = {MAX_SIG_RESETS};" in js)
    ok &= check("js: мигает пока armed или недавно было", "return recent && st.since >= 0" in js)
    ok &= check("js: кулдаун гасит сразу", "if (!armed && coolingDown)" in js)
    print("ALL OK" if ok else "ЕСТЬ ОШИБКИ")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
