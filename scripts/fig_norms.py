"""Figure: what greenery norms normalise, with verified examples (sources in docs/research/)."""
import sys

import matplotlib.pyplot as plt

from bgreen.viz import style as S

ROWS = {
    "ru": [
        ("м² на жителя", [
            "Россия, СП 42.13330.2026: ≥ 10 м² озеленённых территорий общего пользования в городах",
            "Берлин: 6 м² «у дома» (парк ≥ 0,5 га в 500 м) + 7 м² «у района» (парк > 10 га в 1–1,5 км)",
            "Сингапур: 0,8 га парков на 1000 жителей (8 м²)",
            "Китай, «город-сад» (2016): 8–9 м², «эко-город-сад» — 10–12 м²"]),
        ("доля территории", [
            "Россия, СП 42.13330.2016: ≥ 25% площади квартала; в СП 2026 это отдано правилам застройки",
            "Белград, план системы зелени (2019): 10–40% участка в прямом контакте с грунтом, по зонам",
            "Англия, Natural England (2023): ≥ 40% зелёного покрова в жилых районах"]),
        ("доступность", [
            "ВОЗ Европа (2017): 0,5–1 га общественной зелени в 300 м по прямой — «эмпирическое правило»",
            "Англия (2023): 2 га в 300 м, 10 га в 1 км, 100 га в 5 км, 500 га в 10 км",
            "Белград (2019): 7 / 10 / 23 м² общественной зелени и леса на жителя квартала в радиусе 300 м"]),
        ("кроны", [
            "ЕС, регламент 2024/1991: без чистых потерь зелени и крон к 2030 (база 2024), затем рост",
            "Мельбурн: 22% → 40% к 2040 (публичные территории) · Барселона: 25% → 30% к 2037 · Торонто: 40% к 2050",
            "3-30-300: ≥ 30% крон в каждом квартале"]),
        ("видимость", [
            "3-30-300: из дома, школы и офиса видно ≥ 3 деревьев (Konijnendijk, 2021–2023)"]),
    ],
    "en": [
        ("m² per resident", [
            "Russia, SP 42.13330.2026: ≥ 10 m² of public green space per resident in towns",
            "Berlin: 6 m² near home (park ≥ 0.5 ha within 500 m) + 7 m² near district (> 10 ha, 1–1.5 km)",
            "Singapore: 0.8 ha of park per 1,000 residents (8 m²)",
            "China, Garden City (2016): 8–9 m²; Eco-Garden City: 10–12 m²"]),
        ("share of land", [
            "Russia, SP 42.13330.2016: ≥ 25% of a residential block; the 2026 code leaves it to zoning rules",
            "Belgrade green-system plan (2019): 10–40% of a plot as green on natural soil, by zone",
            "England, Natural England (2023): ≥ 40% green cover in residential neighbourhoods"]),
        ("access", [
            "WHO Europe (2017): 0.5–1 ha of public green within 300 m straight-line distance (rule of thumb)",
            "England (2023): 2 ha within 300 m, 10 ha within 1 km, 100 ha within 5 km, 500 ha within 10 km",
            "Belgrade (2019): 7 / 10 / 23 m² of public green and forest per block resident within 300 m"]),
        ("canopy", [
            "EU Regulation 2024/1991: no net loss of urban green space and canopy by 2030 (2024 baseline)",
            "Melbourne: 22% → 40% by 2040 (public land) · Barcelona: 25% → 30% by 2037 · Toronto: 40% by 2050",
            "3-30-300: ≥ 30% canopy in every neighbourhood"]),
        ("visibility", [
            "3-30-300: ≥ 3 trees visible from every home, school and workplace (Konijnendijk, 2021–2023)"]),
    ],
}
T = {"ru": {"title": "Что нормируют, когда нормируют зелень",
            "sub": "Пять подходов и примеры. Источники и цитаты — в docs/research/ репозитория",
            "src": "Сбор и проверка: Мария Эрцеговац.\nНормы «9 м² на жителя от ВОЗ» нет ни в одном найденном документе ВОЗ"},
     "en": {"title": "What greenery norms actually normalise",
            "sub": "Five approaches with examples. Sources and quotes in docs/research/ of the repository",
            "src": "Compiled and checked by Marija Ercegovac.\nNo WHO document found sets the often-quoted norm of 9 m² per resident"}}


def main(lang="ru"):
    S.setup()
    t = T[lang]
    fig = plt.figure(figsize=(5.4, 6.75))
    fig.text(0.06, 0.955, t["title"], fontsize=13, fontweight="semibold", va="top")
    fig.text(0.06, 0.915, t["sub"], fontsize=7.8, color=S.INK2, va="top")
    y = 0.865
    for k, (head, items) in enumerate(ROWS[lang]):
        fig.add_artist(plt.Line2D([0.06, 0.94], [y + 0.012, y + 0.012], color=S.GRID, lw=0.6))
        fig.text(0.06, y, f"{k + 1}  {head}", fontsize=9.5, fontweight="semibold", va="top", color=S.INK)
        y -= 0.031
        for it in items:
            words, line, lines = it.split(" "), "", []
            for w in words:
                if len(line) + len(w) + 1 > 84:
                    lines.append(line)
                    line = w
                else:
                    line = (line + " " + w).strip()
            lines.append(line)
            fig.text(0.09, y, "—", fontsize=7.3, color=S.MUTED, va="top")
            fig.text(0.115, y, "\n".join(lines), fontsize=7.3, color=S.INK2, va="top", linespacing=1.3)
            y -= 0.0195 * len(lines) + 0.007
        y -= 0.008
    fig.text(0.06, 0.022, t["src"], fontsize=6.2, color=S.MUTED, linespacing=1.4)
    out = f"reports/figures/p2_norms_{lang}.png"
    fig.savefig(out)
    print(out, "last y", round(y, 3))


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["ru"]))
