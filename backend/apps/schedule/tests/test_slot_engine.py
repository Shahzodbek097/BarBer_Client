"""Bosqich 4: slot dvigateli matritsasi (sof funksiya — DB'siz).

Yarim ochiq oraliq mantig'i: [start, end) — "aynan tegish" kesishmaydi.
"""

from datetime import date, datetime, time

from apps.schedule.services.slots import Slot, compute_day_slots

# Test uchun qat'iy sana (hafta kuni muhim emas — dvigatel sanadan faqat
# "bugun filtri" uchun foydalanadi)
DAY = date(2030, 1, 14)


class TestBasicGrid:
    def test_simple_day_steps(self):
        slots = compute_day_slots(DAY, 30, time(9, 0), time(10, 0))

        assert [(s.start, s.end) for s in slots] == [
            (time(9, 0), time(9, 30)),
            (time(9, 15), time(9, 45)),
            (time(9, 30), time(10, 0)),
        ]

    def test_exact_fit_one_slot(self):
        slots = compute_day_slots(DAY, 60, time(9, 0), time(10, 0))

        assert slots == [Slot(time(9, 0), time(10, 0))]

    def test_duration_exceeds_work_day(self):
        assert compute_day_slots(DAY, 600, time(9, 0), time(10, 0)) == []

    def test_closed_day_no_schedule(self):
        assert compute_day_slots(DAY, 30, None, None) == []

    def test_zero_duration_rejected(self):
        assert compute_day_slots(DAY, 0, time(9, 0), time(18, 0)) == []

    def test_zero_step_rejected(self):
        assert compute_day_slots(DAY, 30, time(9, 0), time(18, 0), step_min=0) == []

    def test_custom_step(self):
        slots = compute_day_slots(DAY, 30, time(9, 0), time(10, 30), step_min=30)

        assert [s.start for s in slots] == [time(9, 0), time(9, 30), time(10, 0)]

    def test_slots_sorted_by_start(self):
        slots = compute_day_slots(DAY, 30, time(9, 0), time(12, 0))

        assert slots == sorted(slots)


class TestBreaks:
    def test_break_excludes_only_overlapping(self):
        slots = compute_day_slots(
            DAY, 30, time(9, 0), time(11, 0), breaks=[(time(10, 0), time(10, 30))]
        )
        starts = [s.start for s in slots]

        assert time(9, 30) in starts  # 09:30-10:00 aynan tanaffus boshida tugaydi
        assert time(9, 45) not in starts  # 09:45-10:15 kesishadi
        assert time(10, 0) not in starts
        assert time(10, 15) not in starts  # 10:15-10:45 kesishadi
        assert time(10, 30) in starts  # tanaffus aynan tugaganida boshlanadi

    def test_multiple_breaks(self):
        slots = compute_day_slots(
            DAY,
            30,
            time(9, 0),
            time(12, 0),
            breaks=[(time(10, 0), time(10, 30)), (time(11, 0), time(11, 30))],
        )
        starts = [s.start for s in slots]

        assert time(9, 30) in starts
        assert time(9, 45) not in starts
        assert time(10, 30) in starts  # 10:30-11:00 ikkinchi tanaffus boshida tugaydi
        assert time(10, 45) not in starts  # 10:45-11:15 ikkinchi tanaffusga tegadi
        assert time(11, 0) not in starts
        assert time(11, 30) in starts

    def test_break_covers_entire_day(self):
        assert (
            compute_day_slots(DAY, 30, time(9, 0), time(12, 0), breaks=[(time(9, 0), time(12, 0))])
            == []
        )


class TestBusy:
    def test_busy_excludes_overlapping(self):
        slots = compute_day_slots(
            DAY, 30, time(9, 0), time(11, 0), busy=[(time(10, 0), time(10, 30))]
        )
        starts = [s.start for s in slots]

        assert time(9, 30) in starts
        assert time(9, 45) not in starts
        assert time(10, 0) not in starts
        assert time(10, 15) not in starts
        assert time(10, 30) in starts

    def test_busy_exact_boundaries_do_not_overlap(self):
        slots = compute_day_slots(
            DAY, 30, time(9, 0), time(11, 0), busy=[(time(9, 30), time(10, 0))]
        )
        starts = [s.start for s in slots]

        assert time(9, 0) in starts  # slot band bo'lgandan oldin tugaydi
        assert time(10, 0) in starts  # slot band tugaganidan keyin boshlanadi
        assert time(9, 15) not in starts
        assert time(9, 45) not in starts

    def test_multiple_busy_intervals(self):
        slots = compute_day_slots(
            DAY, 60, time(9, 0), time(12, 0), busy=[(time(10, 0), time(11, 0))]
        )
        starts = [s.start for s in slots]

        # 09:00-10:00 band oldin, 11:00-12:00 band keyin
        assert starts == [time(9, 0), time(11, 0)]


class TestPastFilter:
    def test_today_past_slots_filtered(self):
        now = datetime(2030, 1, 14, 9, 40)

        slots = compute_day_slots(DAY, 30, time(9, 0), time(11, 0), now=now)

        starts = [s.start for s in slots]
        assert time(9, 0) not in starts
        assert time(9, 30) not in starts  # 09:30 <= 09:40
        assert time(9, 45) in starts  # 09:45 > 09:40

    def test_other_day_not_filtered(self):
        now = datetime(2030, 1, 13, 23, 0)  # kecha

        slots = compute_day_slots(DAY, 30, time(9, 0), time(10, 0), now=now)

        assert [s.start for s in slots] == [time(9, 0), time(9, 15), time(9, 30)]

    def test_whole_day_in_past(self):
        now = datetime(2030, 1, 15, 10, 0)  # ertaga

        assert compute_day_slots(DAY, 30, time(9, 0), time(18, 0), now=now) == []
