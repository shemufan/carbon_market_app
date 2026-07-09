import unittest

import pandas as pd

from analysis_engine import AnalysisThresholds, analyze_all_pairs
from data_loader import apply_row_ranges, parse_row_ranges
from exporter import to_excel_bytes
from significance import add_significance, exact_binomial_point_probability


class AnalysisEngineTests(unittest.TestCase):
    def test_up_cross_uses_descending_date_index_direction(self):
        df = pd.DataFrame(
            {
                "Mean": [99, 101, 102, 100, 98],
                "Mean1": [12, 12, 12, 12, 8],
                "Mean2": [10, 10, 10, 10, 10],
            }
        )

        result = analyze_all_pairs(
            df,
            min_ma=1,
            max_ma=2,
            cross_types=["up"],
            alpha=0.1,
        )

        day1 = result.loc[result["day"] == 1].iloc[0]
        self.assertEqual(day1["pair"], "1/2")
        self.assertEqual(day1["cross_type"], "up")
        self.assertEqual(day1["signal_count"], 1)
        self.assertEqual(day1["up_count"], 1)
        self.assertEqual(day1["down_count"], 0)

    def test_down_cross_is_reverse_condition(self):
        df = pd.DataFrame(
            {
                "Mean": [106, 104, 100, 98],
                "Mean1": [12, 8, 11, 12],
                "Mean2": [10, 10, 9, 10],
                "ChangeRate": [0.03, 0.02, -0.01, 0.01],
            }
        )

        result = analyze_all_pairs(
            df,
            min_ma=1,
            max_ma=2,
            cross_types=["down"],
            alpha=0.1,
        )

        day1 = result.loc[result["day"] == 1].iloc[0]
        self.assertEqual(day1["cross_type"], "down")
        self.assertEqual(day1["up_count"], 1)
        self.assertEqual(day1["down_count"], 0)

    def test_future_days_compare_against_previous_day_not_cross_day(self):
        df = pd.DataFrame(
            {
                # Descending date order: index 3 is the cross day. Days after
                # the signal are index 2, 1, 0 with prices 110, 105, 120.
                "Mean": [120, 105, 110, 100, 95],
                "Mean1": [12, 12, 12, 12, 8],
                "Mean2": [10, 10, 10, 10, 10],
            }
        )

        result = analyze_all_pairs(
            df,
            min_ma=1,
            max_ma=2,
            cross_types=["up"],
            alpha=0.1,
        )

        day1 = result.loc[result["day"] == 1].iloc[0]
        day2 = result.loc[result["day"] == 2].iloc[0]
        day3 = result.loc[result["day"] == 3].iloc[0]

        self.assertEqual(day1["up_count"], 1)
        self.assertEqual(day1["down_count"], 0)
        self.assertEqual(day2["up_count"], 0)
        self.assertEqual(day2["down_count"], 1)
        self.assertEqual(day3["up_count"], 1)
        self.assertEqual(day3["down_count"], 0)

    def test_threshold_screening_changes_when_thresholds_change(self):
        df = pd.DataFrame(
            {
                "Mean": [99, 101, 102, 100, 98],
                "Mean1": [12, 12, 12, 12, 8],
                "Mean2": [10, 10, 10, 10, 10],
            }
        )

        loose_result = analyze_all_pairs(
            df,
            min_ma=1,
            max_ma=2,
            cross_types=["up"],
            alpha=0.1,
            thresholds=AnalysisThresholds(high=60, low=40, three_day=25),
        )
        strict_result = analyze_all_pairs(
            df,
            min_ma=1,
            max_ma=2,
            cross_types=["up"],
            alpha=0.1,
            thresholds=AnalysisThresholds(high=101, low=-1, three_day=25),
        )

        loose_day1 = loose_result.loc[loose_result["day"] == 1].iloc[0]
        strict_day1 = strict_result.loc[strict_result["day"] == 1].iloc[0]

        self.assertTrue(bool(loose_day1["threshold_triggered"]))
        self.assertIn("up_ratio > 60%", loose_day1["threshold_alerts"])
        self.assertFalse(bool(strict_day1["threshold_triggered"]))
        self.assertEqual(strict_day1["threshold_alerts"], "")

    def test_three_day_threshold_screens_complete_combo_on_day3(self):
        df = pd.DataFrame(
            {
                # One up-cross at index 3. The following three days form
                # combo 1,-1,1: 100 -> 110 -> 105 -> 120.
                "Mean": [120, 105, 110, 100, 95],
                "Mean1": [12, 12, 12, 12, 8],
                "Mean2": [10, 10, 10, 10, 10],
            }
        )

        loose_result = analyze_all_pairs(
            df,
            min_ma=1,
            max_ma=2,
            cross_types=["up"],
            alpha=0.1,
            thresholds=AnalysisThresholds(high=101, low=-1, three_day=50),
        )
        strict_result = analyze_all_pairs(
            df,
            min_ma=1,
            max_ma=2,
            cross_types=["up"],
            alpha=0.1,
            thresholds=AnalysisThresholds(high=101, low=-1, three_day=100),
        )

        loose_day3 = loose_result.loc[loose_result["day"] == 3].iloc[0]
        strict_day3 = strict_result.loc[strict_result["day"] == 3].iloc[0]

        self.assertTrue(bool(loose_day3["threshold_triggered"]))
        self.assertIn("3day_combo 1,-1,1 > 50%", loose_day3["threshold_alerts"])
        self.assertFalse(bool(strict_day3["threshold_triggered"]))
        self.assertEqual(strict_day3["threshold_alerts"], "")

    def test_parse_and_apply_row_ranges(self):
        df = pd.DataFrame({"Mean": range(5)})

        ranges = parse_row_ranges("0-1, 3, 10-20")
        selected = apply_row_ranges(df, ranges)

        self.assertEqual(selected["Mean"].tolist(), [0, 1, 3])

    def test_significance_ignores_flat_count(self):
        df = pd.DataFrame(
            [
                {
                    "up_count": 9,
                    "down_count": 1,
                    "flat_count": 10,
                    "up_ratio": 0.45,
                    "down_ratio": 0.05,
                }
            ]
        )

        enriched = add_significance(df, alpha=0.1)

        self.assertLess(enriched.loc[0, "p_value"], 0.1)
        self.assertTrue(bool(enriched.loc[0, "is_significant"]))
        self.assertAlmostEqual(enriched.loc[0, "jeffreys_up_prob"], 9.5 / 11)

    def test_significance_detects_all_down_days(self):
        df = pd.DataFrame(
            [
                {
                    "pair": "1/2",
                    "cross_type": "down",
                    "day": 1,
                    "signal_count": 9,
                    "up_count": 0,
                    "down_count": 9,
                    "flat_count": 0,
                    "up_ratio": 0.0,
                    "down_ratio": 1.0,
                }
            ]
        )

        enriched = add_significance(df, alpha=0.1)

        self.assertLess(enriched.loc[0, "p_value"], 0.01)
        self.assertTrue(bool(enriched.loc[0, "is_significant"]))
        self.assertAlmostEqual(enriched.loc[0, "jeffreys_down_prob"], 0.95)

    def test_significance_does_not_flag_balanced_counts(self):
        df = pd.DataFrame(
            [
                {
                    "pair": "1/2",
                    "cross_type": "up",
                    "day": 1,
                    "signal_count": 10,
                    "up_count": 5,
                    "down_count": 5,
                    "flat_count": 0,
                    "up_ratio": 0.5,
                    "down_ratio": 0.5,
                }
            ]
        )

        enriched = add_significance(df, alpha=0.1)

        self.assertAlmostEqual(enriched.loc[0, "p_value"], 0.24609375)
        self.assertFalse(bool(enriched.loc[0, "is_significant"]))

    def test_exact_point_probability_matches_coin_example(self):
        self.assertAlmostEqual(exact_binomial_point_probability(9, 10, 0.5), 0.009765625)

    def test_exact_point_probability_matches_project_example(self):
        self.assertAlmostEqual(
            exact_binomial_point_probability(18, 59, 0.5),
            0.0011232693525645,
        )

    def test_mvp_excel_export_returns_bytes(self):
        df = pd.DataFrame(
            {
                "pair": ["1/2"],
                "cross_type": ["up"],
                "day": [1],
                "signal_count": [1],
                "up_count": [1],
                "down_count": [0],
                "flat_count": [0],
                "up_ratio": [1.0],
                "down_ratio": [0.0],
                "p_value": [1.0],
                "is_significant": [False],
                "jeffreys_up_prob": [0.75],
                "jeffreys_down_prob": [0.25],
            }
        )

        data = to_excel_bytes(df, df[df["is_significant"]])

        self.assertGreater(len(data), 1000)


if __name__ == "__main__":
    unittest.main()
