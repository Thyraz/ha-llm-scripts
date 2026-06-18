from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "python_scripts" / "llmtool_calculator.py"


def run_helper(overrides):
    data = {
        "operation": "sum",
        "values": "1,2,3",
        "precision": "",
    }
    data.update(overrides)

    output = {}
    exec(SCRIPT.read_text(), {"data": data, "output": output})
    return output


class CalculatorHelperTest(unittest.TestCase):
    def test_sum_returns_numeric_result_and_values(self):
        result = run_helper({"operation": "sum", "values": "1,2,3"})

        self.assertTrue(result["success"])
        self.assertEqual(6, result["data"]["result"])
        self.assertEqual([1, 2, 3], result["data"]["values"])
        self.assertEqual("sum", result["meta"]["operation"])
        self.assertEqual(3, result["meta"]["value_count"])

    def test_difference_and_quotient_preserve_order(self):
        difference = run_helper({"operation": "difference", "values": "10,2,3"})
        quotient = run_helper({"operation": "quotient", "values": "100,2,5"})

        self.assertEqual(5, difference["data"]["result"])
        self.assertEqual(10, quotient["data"]["result"])

    def test_product_minimum_maximum_and_average(self):
        product = run_helper({"operation": "product", "values": "2,3,4"})
        minimum = run_helper({"operation": "minimum", "values": "-1,3,2"})
        maximum = run_helper({"operation": "maximum", "values": "-1,3,2"})
        average = run_helper({"operation": "average", "values": "2,4,6"})

        self.assertEqual(24, product["data"]["result"])
        self.assertEqual(-1, minimum["data"]["result"])
        self.assertEqual(3, maximum["data"]["result"])
        self.assertEqual(4, average["data"]["result"])

    def test_average_one_value_is_valid(self):
        result = run_helper({"operation": "average", "values": "2.5"})

        self.assertTrue(result["success"])
        self.assertEqual(2.5, result["data"]["result"])

    def test_precision_rounds_result_and_keeps_raw_result(self):
        result = run_helper({"operation": "quotient", "values": "10,3", "precision": "2"})

        self.assertTrue(result["success"])
        self.assertEqual(3.33, result["data"]["result"])
        self.assertEqual(3.3333333333333335, result["data"]["raw_result"])
        self.assertEqual(2, result["meta"]["precision"])

    def test_integer_valued_float_precision_is_valid(self):
        result = run_helper({"operation": "quotient", "values": "10,3", "precision": "2.0"})

        self.assertTrue(result["success"])
        self.assertEqual(3.33, result["data"]["result"])

    def test_empty_precision_omits_raw_result(self):
        result = run_helper({"operation": "sum", "values": "1,2", "precision": ""})

        self.assertTrue(result["success"])
        self.assertNotIn("raw_result", result["data"])
        self.assertNotIn("precision", result["meta"])

    def test_negative_zero_normalizes_to_zero(self):
        result = run_helper({"operation": "difference", "values": "1,1"})

        self.assertTrue(result["success"])
        self.assertEqual(0, result["data"]["result"])
        self.assertEqual("Result: 0.", result["answer"])

    def test_invalid_operation_returns_known_operations(self):
        result = run_helper({"operation": "avg", "values": "1,2"})

        self.assertFalse(result["success"])
        self.assertIn("average", result["data"]["known_operations"])

    def test_missing_values_returns_soft_failure(self):
        result = run_helper({"operation": "sum", "values": ""})

        self.assertFalse(result["success"])
        self.assertEqual(1, result["data"]["required_values"])

    def test_difference_and_quotient_require_two_values(self):
        difference = run_helper({"operation": "difference", "values": "1"})
        quotient = run_helper({"operation": "quotient", "values": "1"})

        self.assertFalse(difference["success"])
        self.assertFalse(quotient["success"])
        self.assertEqual(2, difference["data"]["required_values"])
        self.assertEqual(2, quotient["data"]["required_values"])

    def test_invalid_decimal_tokens_include_positions(self):
        result = run_helper({"operation": "sum", "values": "1,21 C,1e3,,unknown"})

        self.assertFalse(result["success"])
        self.assertEqual(
            [
                {"token": "21 C", "position": 2},
                {"token": "1e3", "position": 3},
                {"token": "", "position": 4},
                {"token": "unknown", "position": 5},
            ],
            result["data"]["invalid_values"],
        )

    def test_decimal_comma_is_separator_not_decimal_separator(self):
        result = run_helper({"operation": "sum", "values": "1,5"})

        self.assertTrue(result["success"])
        self.assertEqual([1, 5], result["data"]["values"])
        self.assertEqual(6, result["data"]["result"])

    def test_division_by_zero_returns_soft_failure(self):
        result = run_helper({"operation": "quotient", "values": "10,2,0"})

        self.assertFalse(result["success"])
        self.assertEqual([3], result["data"]["zero_divisor_positions"])

    def test_more_than_1000_values_returns_soft_failure(self):
        values = ",".join(["1"] * 1001)

        result = run_helper({"operation": "sum", "values": values})

        self.assertFalse(result["success"])
        self.assertEqual(1000, result["data"]["max_values"])
        self.assertEqual(1001, result["data"]["value_count"])

    def test_invalid_precision_returns_soft_failure(self):
        text_precision = run_helper({"operation": "sum", "values": "1,2", "precision": "2.5"})
        large_precision = run_helper({"operation": "sum", "values": "1,2", "precision": "11"})

        self.assertFalse(text_precision["success"])
        self.assertFalse(large_precision["success"])

    def test_non_finite_result_returns_soft_failure(self):
        huge_value = "1" + ("0" * 200)

        result = run_helper({"operation": "product", "values": huge_value + "," + huge_value})

        self.assertFalse(result["success"])
        self.assertIn("not finite", result["error"])


if __name__ == "__main__":
    unittest.main()
