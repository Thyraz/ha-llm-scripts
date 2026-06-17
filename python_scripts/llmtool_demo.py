# Normalize the optional demo input.
raw_name = data.get("name", "")
normalized_name = str(raw_name).strip()

if not normalized_name:
    normalized_name = "World"

# Build the simple helper response returned to the LLM Tool Script.
helper_message = "Hello {}, this came from the LLM Tool Python Helper.".format(
    normalized_name
)

# Native python_script returns data by writing to output.
output["normalized_name"] = normalized_name
output["helper_message"] = helper_message
