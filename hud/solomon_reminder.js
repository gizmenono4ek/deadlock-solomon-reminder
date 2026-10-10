// Solomon Piece Reminder
// Скрипт живёт внутри каждой иконки способности (panorama/layout/hud_ability_icon.xml -> CitadelAbilityIcon).
// Пока иконка в состоянии «фигура выставлена, нажми ещё раз» (классы active / toggled_on / is_trigger),
// считаем время. Прошло DELAY_SECONDS -> класс solomon_overdue, по нему CSS (solomon_reminder.css) мигает иконкой.
// Взаимодействие с фигурой (переставил, перезарядило) меняет классы прогресса на иконках фигур под способностью
// (#ability_subcasts: has_progress / is_progress_*) - отсчёт начинается заново.
// Состояние снято и пошёл кулдаун (фигуру убрали) -> мигание гаснет сразу. Состояние снято без кулдауна
// (тяжёлая атака, слайд, стан на миг глушат иконки) -> мигание и отсчёт продолжаются до GRACE_SECONDS.
// DELAY_SECONDS и SOLOMON_ONLY подставляет solomon_reminder.py при сборке.
// Логика в чистой функции step(): её копия в tests/test_logic.py прогоняется сценариями.
"use strict";

(function () {
    const DELAY_SECONDS = __DELAY__;
    const SOLOMON_ONLY = __SOLOMON_ONLY__;      // true: только иконки Соломона (классы subcast_chessmaster_*)
    const GRACE_SECONDS = 3;                // столько состояние может пропасть, не сбрасывая отсчёт
    const POLL = 0.5;
    const ON_STATES = ["active", "toggled_on", "is_trigger"];
    const SOLOMON_CLASSES = ["subcast_chessmaster_bishop", "subcast_chessmaster_knight", "subcast_chessmaster_queen"];
    // В слепок НЕ входят is_selected (игра выделяет фигуру, когда на неё смотришь - дёргалось бы при каждом повороте)
    // и cooling_down/held (мигают от чужих действий). Только то, что меняется, когда с фигурой реально что-то сделали.
    const ROOT_FLAGS = ["channeling"];
    const SUBCAST_FLAGS = ["has_progress", "is_progress_active", "is_progress_inactive", "is_king"];
    const OVERDUE = "solomon_overdue";

    const self = $.GetContextPanel();
    const MAX_SIG_RESETS = 3;               // больше перезапусков от слепка за одно состояние = это шум, а не действия
    const st = { since: -1, lastOn: -1, sig: "", sigResets: 0 };   // since: когда появилось; lastOn: когда видели в последний раз

    function alive(p) {
        try { return !!p && p.IsValid(); } catch (e) { return false; }
    }

    function hasAny(panel, classes) {
        for (let i = 0; i < classes.length; i++) {
            if (panel.BHasClass(classes[i])) return true;
        }
        return false;
    }

    function flags(panel, classes) {
        let s = "";
        for (let i = 0; i < classes.length; i++) s += panel.BHasClass(classes[i]) ? "1" : "0";
        return s;
    }

    // Снимок состояния фигур под иконкой: классы корня + классы иконок фигур (#ability_subcasts и их дети).
    function signature() {
        let s = flags(self, ROOT_FLAGS);
        const subs = self.FindChildTraverse("ability_subcasts");
        if (!alive(subs)) return s;
        for (let i = 0; i < subs.GetChildCount(); i++) {
            const c = subs.GetChild(i);
            s += "|" + flags(c, SUBCAST_FLAGS);
            for (let j = 0; j < c.GetChildCount(); j++) s += flags(c.GetChild(j), SUBCAST_FLAGS);
        }
        return s;
    }

    // Чистая логика (зеркало - tests/test_logic.py). armed: состояние «фигура выставлена» есть сейчас,
    // coolingDown: на иконке класс cooling_down, sig: снимок классов фигур, now: мс. true = пора мигать.
    function step(st, armed, coolingDown, sig, now) {
        if (!armed && coolingDown) {
            st.since = -1;                  // способность ушла на кулдаун = фигуру убрали/активировали
        } else if (armed) {
            if (st.since < 0) {
                st.since = now;             // состояние появилось
                st.sig = sig;
                st.sigResets = 0;
            } else if (sig !== st.sig) {
                st.sig = sig;               // с фигурой что-то сделали - отсчёт заново (пока это не похоже на шум)
                if (st.sigResets < MAX_SIG_RESETS) {
                    st.sigResets++;
                    st.since = now;
                }
            }
            st.lastOn = now;
        } else if (st.since >= 0 && now - st.lastOn > GRACE_SECONDS * 1000) {
            st.since = -1;
        }
        const recent = armed || now - st.lastOn <= GRACE_SECONDS * 1000;
        return recent && st.since >= 0 && now - st.since >= DELAY_SECONDS * 1000;
    }

    function update() {
        const armed = hasAny(self, ON_STATES) && (!SOLOMON_ONLY || hasAny(self, SOLOMON_CLASSES));
        self.SetHasClass(OVERDUE, step(st, armed, self.BHasClass("cooling_down"), armed ? signature() : st.sig, Date.now()));
    }

    function loop() {
        if (!alive(self)) return;          // иконку пересоздали - этот экземпляр скрипта больше не нужен
        try { update(); } catch (e) { $.Msg("[SolomonReminder] " + e); }
        $.Schedule(POLL, loop);
    }

    loop();
})();
