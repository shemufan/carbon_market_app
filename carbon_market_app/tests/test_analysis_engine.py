import unittest

import pandas as pd

from analysis_engine import analyze_all_pairs
from data_loader import apply_row_ranges, parse_row_ranges
from significance import add_significance, exact_binomtest_pvalue


class AnalysisEngineTests(unittest.TestCase):
    def test_up_cross_uses_descending_date_index_direction(self):
        df = pd.DataFrame(
            {
                "Mean": [99, 101, 102, 100, 98],
                "Mean1": [12, 12, 12, 12, 8],
                "Mean2": [10, 10, 10, 10, 10],
            }
        )

        result, combos = analyze_all_pairs(
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
        self.assertEqual(combos.iloc[0]["combo"], "1,1,-1")

    def test_down_cross_is_reverse_condition(self):
        df = pd.DataFrame(
            {
                "Mean": [106, 104, 100, 98],
                "Mean1": [12, 8, 11, 12],
                "Mean2": [10, 10, 9, 10],
                "ChangeRate": [0.03, 0.02, -0.01, 0.01],
            }
        )

        result, _ = analyze_all_pairs(
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

    def test_exact_binomtest_matches_two_sided_coin_example(self):
        self.assertAlmostEqual(exact_binomtest_pvalue(9, 10, 0.5), 0.021484375)


if __name__ == "__main__":
    unittest.main()
