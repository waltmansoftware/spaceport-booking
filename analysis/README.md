# Analysis

This folder contains investigations and reproducible calculations that support the assessment without becoming part of the running application.

- `capacity-and-utilization.md` documents annual fleet capacity and compares the combined file's consecutive periods.
- `seed_utilization.py` calculates flight, refueling, busy, and available time for a chosen date window.
- `test_seed.py` verifies randomized history, light coverage of the next seven days, record validity, and reproducibility when a random seed is supplied.
- `test_seed_utilization.py` checks the calculation rules independently of Django.

Run the analysis and its tests from the repository root:

```sh
python analysis/seed_utilization.py \
  --start 2025-09-30 --end 2026-09-30 \
  seed.json

python analysis/seed_utilization.py \
  --start 2026-09-30 --end 2027-09-30 \
  seed.json

python -m unittest analysis.test_seed analysis.test_seed_utilization
```
