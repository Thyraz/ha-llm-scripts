MAX_VALUES = 1000
MAX_PRECISION = 10

OPERATIONS = [
    "sum",
    "difference",
    "product",
    "quotient",
    "minimum",
    "maximum",
    "average",
]


# Small helpers keep the top-level python_script flow readable.
def as_text(value):
    if value is None:
        return ""
    return str(value).strip()


def validation_error(message, data_payload=None, meta_payload=None):
    output["success"] = False
    output["error"] = message
    output["data"] = data_payload or {}
    output["meta"] = meta_payload or {"tool": "llmtool_calculator"}


def is_decimal_token(token):
    if not token:
        return False

    value = token
    if value[0] == "-":
        value = value[1:]

    if not value:
        return False

    dot_count = 0
    digit_count = 0
    for char in value:
        if char == ".":
            dot_count = dot_count + 1
            if dot_count > 1:
                return False
        elif char >= "0" and char <= "9":
            digit_count = digit_count + 1
        else:
            return False

    return digit_count > 0


def normalize_number(value):
    if value == 0:
        return 0

    rounded = round(value, 12)
    if rounded == 0:
        return 0

    integer_value = int(rounded)
    if rounded == integer_value:
        return integer_value

    return rounded


def normalize_raw_number(value):
    if value == 0:
        return 0

    integer_value = int(value)
    if value == integer_value:
        return integer_value

    return value


def answer_number(value):
    return str(value)


# Normalize caller input.
operation = as_text(data.get("operation"))
raw_values = as_text(data.get("values"))
raw_precision = as_text(data.get("precision"))

meta = {"tool": "llmtool_calculator"}

# Validate operation and precision before parsing values.
if operation not in OPERATIONS:
    validation_error(
        "Invalid operation. Use a known Calculator operation.",
        {"known_operations": OPERATIONS},
        meta,
    )

precision = None
if output.get("success") is not False and raw_precision:
    precision_is_int = True
    precision_text = raw_precision
    if "." in precision_text:
        precision_parts = precision_text.split(".")
        if len(precision_parts) == 2 and precision_parts[1] == "0":
            precision_text = precision_parts[0]
        else:
            precision_is_int = False

    if precision_text == "":
        precision_is_int = False

    if precision_is_int:
        for char in precision_text:
            if char < "0" or char > "9":
                precision_is_int = False

    if not precision_is_int:
        validation_error(
            "Invalid precision. Use an integer from 0 to 10.",
            {"min_precision": 0, "max_precision": MAX_PRECISION},
            meta,
        )
    else:
        precision = int(precision_text)
        if precision < 0 or precision > MAX_PRECISION:
            validation_error(
                "Invalid precision. Use an integer from 0 to 10.",
                {"min_precision": 0, "max_precision": MAX_PRECISION},
                meta,
            )

if output.get("success") is not False:
    # Parse strict decimal tokens. Commas always delimit values.
    raw_parts = raw_values.split(",")
    values = []
    invalid_values = []
    positive_inf = float("inf")

    for index in range(len(raw_parts)):
        token = raw_parts[index].strip()
        position = index + 1

        if not is_decimal_token(token):
            invalid_values.append({"token": token, "position": position})
        else:
            value = float(token)
            if value == positive_inf or value == -positive_inf or value != value:
                invalid_values.append({"token": token, "position": position})
            else:
                values.append(value)

    if raw_values == "":
        validation_error(
            "Missing values. Provide comma-separated decimal numbers.",
            {"required_values": 1},
            meta,
        )
    elif invalid_values:
        validation_error(
            "Invalid Calculator value. Use decimal numbers with '.' as decimal separator.",
            {
                "invalid_values": invalid_values,
                "expected": "Comma-separated decimal numbers without units. Commas separate values; use '.' for decimals.",
            },
            meta,
        )
    elif len(values) > MAX_VALUES:
        validation_error(
            "Too many values. Use at most 1000 values.",
            {"max_values": MAX_VALUES, "value_count": len(values)},
            meta,
        )

if output.get("success") is not False:
    # Validate operation-specific arity and divisor values.
    min_values = 1
    if operation == "difference" or operation == "quotient":
        min_values = 2

    if len(values) < min_values:
        validation_error(
            "Too few values for operation.",
            {
                "operation": operation,
                "required_values": min_values,
                "value_count": len(values),
            },
            meta,
        )

if output.get("success") is not False and operation == "quotient":
    zero_divisor_positions = []
    for index in range(1, len(values)):
        if values[index] == 0:
            zero_divisor_positions.append(index + 1)

    if zero_divisor_positions:
        validation_error(
            "Division by zero. Remove or replace zero divisors.",
            {"zero_divisor_positions": zero_divisor_positions},
            meta,
        )

if output.get("success") is not False:
    # Calculate using Python's native numeric behavior inside python_script.
    if operation == "sum":
        raw_result = 0
        for value in values:
            raw_result = raw_result + value
    elif operation == "difference":
        raw_result = values[0]
        for value in values[1:]:
            raw_result = raw_result - value
    elif operation == "product":
        raw_result = 1
        for value in values:
            raw_result = raw_result * value
    elif operation == "quotient":
        raw_result = values[0]
        for value in values[1:]:
            raw_result = raw_result / value
    elif operation == "minimum":
        raw_result = min(values)
    elif operation == "maximum":
        raw_result = max(values)
    else:
        raw_result = 0
        for value in values:
            raw_result = raw_result + value
        raw_result = raw_result / len(values)

    positive_inf = float("inf")
    if raw_result == positive_inf or raw_result == -positive_inf or raw_result != raw_result:
        validation_error(
            "Calculator result is not finite. Use smaller values.",
            {"operation": operation},
            meta,
        )

if output.get("success") is not False:
    unrounded_result = raw_result
    raw_result = normalize_number(unrounded_result)
    result = raw_result
    if precision is not None:
        result = normalize_number(round(unrounded_result, precision))

    shaped_values = []
    for value in values:
        shaped_values.append(normalize_number(value))

    response_data = {
        "result": result,
        "values": shaped_values,
    }
    if precision is not None:
        response_data["raw_result"] = normalize_raw_number(unrounded_result)

    response_meta = {
        "tool": "llmtool_calculator",
        "operation": operation,
        "value_count": len(values),
    }
    if precision is not None:
        response_meta["precision"] = precision

    output["success"] = True
    output["answer"] = "Result: {}.".format(answer_number(result))
    output["data"] = response_data
    output["meta"] = response_meta
