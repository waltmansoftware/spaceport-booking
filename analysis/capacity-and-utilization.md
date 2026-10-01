# Annual capacity and seed utilization

Calculated September 30, 2026 from the actual local combined `seed.json`. The file contains the supplied timing pattern followed by the aggressive pattern in consecutive 365-day periods. This analysis uses the assessment's fictional charter rules; real-world spacecraft travel times are not additional requirements.

## Capacity assumptions

There are five independently bookable ships. Each is available every day from 06:00 to 22:00 Central: **16 hours, or 960 minutes per day**. Consecutive flights on the same ship require at least 30 minutes between them. Flights have positive duration and must finish that day by 22:00.

As in the application, the final flight may end at 22:00, with its refueling finishing after closing. Only the gaps between flights must fit within the operating window. There are no extra shared launch-pad, maintenance, pilot-availability, or seasonal restrictions in the prompt. DST changes occur outside the operating window, so each operating day still contributes 16 hours.

For a 365-day calendar year:

```text
One ship: 16 × 365 = 5,840 operating hours
Fleet:    16 × 365 × 5 = 29,200 ship-hours
```

A ship-hour means one hour of one ship's capacity. Five ships can accumulate five ship-hours during one clock hour. A leap year provides **29,280 fleet ship-hours**.

## Maximum number of flights in a calendar year

The prompt does not specify a minimum flight duration. The seed generators' duration choices are test-data choices, not application rules. Consequently, the useful maximum depends on the duration assumption.

For a minimum flight duration `d` in minutes and `n` flights on one ship in a day:

```text
Flight time + required gaps <= operating time
n × d + (n − 1) × 30 <= 960
n <= floor(990 / (d + 30))
Annual fleet maximum = daily maximum × number of days × 5
```

| Duration assumption | Maximum per ship/day | Per ship, 365 days | Five ships, 365 days | Five ships, 366 days |
| --- | ---: | ---: | ---: | ---: |
| Positive duration, no stated minimum; sub-minute flights allowed | 32 | 11,680 | **58,400** | 58,560 |
| One-minute minimum, consistent with the current UI's minute inputs | 31 | 11,315 | **56,575** | 56,730 |
| 30-minute minimum, matching the shortest replacement-seed flights | 16 | 5,840 | **29,200** | 29,280 |
| 60-minute minimum, matching the shortest provided-seed flights | 11 | 4,015 | **20,075** | 20,130 |

The unrestricted positive-duration case still has a finite maximum because of refueling. Thirty-three flights require 32 gaps, which alone consume `32 × 30 = 960` minutes, leaving no positive flight time. Thirty-two flights are possible: for example, 30-second flights consume 16 minutes plus 930 minutes of gaps, totaling 946 minutes. These are mathematical bounds, not realistic flight-duration recommendations.

For the minute-input case, 31 one-minute flights consume `31 + 30 × 30 = 931` minutes. Thirty-two would consume 962 minutes, exceeding the day. For 30-minute flights, 16 flights consume 930 minutes including gaps. For 60-minute flights, 11 flights consume exactly 960 minutes.

The duration-based rows assume only the required 30-minute gap, not every implementation detail of a generator. The supplied pattern additionally inserts at least 30 minutes of idle time after refueling and at least 30 minutes after opening before the first flight. With its 60-minute minimum flights and effective 60-minute gaps, it can generate at most eight flights on a single day. Its quota of 600 per ship also stops it long before any annual theoretical maximum. The aggressive pattern deliberately generates ten flights on each of 60 selected days, also totaling 600 per ship; it does not try to maximize annual bookings.

## What “busy” and “available” mean

This comparison separates three uses of operating time:

- **Flight time:** time inside a booked flight.
- **Refueling time:** the next 30 minutes after a flight, counting only the portion before 22:00.
- **Available time:** operating time outside both flight and refueling intervals.

For each ship and Central calendar day, merge occupied intervals `[flight start, flight end + 30 minutes)` after clipping them to 06:00–22:00. Merging prevents double counting. There is **no leading buffer**. This uses the recruiter's clarified rule and matches the corrected availability endpoint.

```text
Busy hours = flight hours + refueling hours within operating hours
Available hours = total operating capacity − busy hours
Busy ratio = busy hours / total operating capacity
Available ratio = available hours / total operating capacity
```

Available hours are an occupancy measure, not a promise that an arbitrary additional flight will fit. Fragmented gaps may be too short for a flight and its own turnaround. In particular, the aggressive period's one-minute idle gaps are generally unusable for another positive-duration flight plus 30 minutes of refueling.

## How busy are the two consecutive periods?

For the reproducible `--today 2026-09-30` generation, the two half-open periods are:

- **Supplied period:** September 30, 2025 through September 29, 2026, written `[2025-09-30, 2026-09-30)`.
- **Aggressive period:** September 30, 2026 through September 29, 2027, written `[2026-09-30, 2027-09-30)`.

The intervals touch at midnight but do not overlap. Each is exactly 365 Central dates and has the same denominator of **29,200 fleet operating hours**. All 3,000 records from each pattern fall within its assigned period.

| Metric | First period: supplied pattern | Second period: aggressive pattern |
| --- | ---: | ---: |
| Bookings within the period | **3,000** | **3,000** |
| Fleet operating capacity | 29,200.00 h | 29,200.00 h |
| Flight time | 6,858.50 h | 3,436.08 h |
| Refueling within operating hours | 1,452.50 h | 1,350.00 h |
| Total busy time | **8,311.00 h** | **4,786.08 h** |
| Remaining available time | **20,889.00 h** | **24,413.92 h** |
| Flight-only utilization | 23.49% | 11.77% |
| Busy ratio, including refueling | **28.46%** | **16.39%** |
| Available ratio | **71.54%** | **83.61%** |
| Ship-days with bookings | 1,199 of 1,825 | 300 of 1,825 |
| Busy ratio on those active ship-days only | **43.32%** | **99.71%** |

A ship-day is one ship on one date. The aggressive period has 60 active dates with all five ships scheduled on each: `60 × 5 = 300` active ship-days. Active-day capacity is `300 × 16 = 4,800 hours`; 4,786.08 hours is occupied and only **13.92 hours** is idle across those days. The other 24,400 available hours come from completely unscheduled ship-days.

The aggressive period is **more tightly packed on scheduled days, but less busy across its whole year**. It places shorter flights into fewer active days. The supplied period spreads longer flights across many more days. The aggressive data is designed to exercise exact turnaround boundaries; it should not be described as a simulation of higher annual demand.

## Reproducing the calculation

The read-only [analysis script](seed_utilization.py) uses Python's standard library and accepts any exclusive date window:

```sh
python analysis/seed_utilization.py \
  --start 2025-09-30 --end 2026-09-30 \
  seed.json

python analysis/seed_utilization.py \
  --start 2026-09-30 --end 2027-09-30 \
  seed.json

python -m unittest analysis.test_seed_utilization
```

It works directly from JSON, without Django or the database. Tests verify trailing-only refueling, clipping at closing, interval merging, Central date conversion, and exclusion of the end date. It measures occupancy; it is not a replacement for the separate booking-validity audit.

For a January-through-December calendar-year view, choose those exclusive boundaries instead. Empty periods in synthetic data represent no generated bookings, not evidence of actual historical business activity. The ratios above describe these fixtures only.

The JSON file is a local, Git-ignored artifact. Regenerating it with another anchor or changing the analysis window changes the results. SHA-256 fingerprint of the file used for this report:

```text
seed.json: c83f49357c5e9bff04698b82df02d1a4e04eaa84ceecb9ce507afc6d57684fd9
```

This analysis does not modify the seed files, booking rules, or database.
