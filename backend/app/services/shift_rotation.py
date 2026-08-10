from __future__ import annotations

from datetime import date

from app.models.organization import Shift

# Formenler artık iki vardiya arasında haftalık dönüşümlüdür (bkz. CLAUDE.md). Bir
# `ForemanAssignment.shift_id`, formenin tenure'ının ilk haftasında hangi vardiyada
# başladığını ("rotasyon çıpası") taşır; belirli bir gündeki GERÇEK vardiya bu sabit,
# global referans tarihe göre hesaplanır. Formenlerin bireysel `start_date`'leri
# birbirinden bağımsız rastgele üretildiğinden (bkz. reference_data.py), parite formenin
# kendi başlangıç tarihine göre değil bu sabit epoch'a göre hesaplanır — aksi halde aynı
# tesisi paylaşan iki formen bazı haftalarda aynı vardiyaya düşebilirdi.
ROTATION_EPOCH = date(2024, 1, 1)


def actual_shift_for_date(d: date, anchor_shift: Shift, shifts: list[Shift]) -> Shift:
    ordered = sorted(shifts, key=lambda s: s.sequence)
    week_index = (d - ROTATION_EPOCH).days // 7
    anchor_idx = ordered.index(anchor_shift)
    return ordered[(anchor_idx + week_index) % len(ordered)]
