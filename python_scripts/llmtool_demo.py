raw_name = data.get("name", "")
normalized_name = str(raw_name).strip()

if not normalized_name:
    normalized_name = "World"

helper_message = "Hello {}, this came from the LLM Tool Python Helper.".format(
    normalized_name
)

output["normalized_name"] = normalized_name
output["helper_message"] = helper_message
