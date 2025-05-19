import csv
import yaml

csv_location = "lcls_elements.csv"
filter_location = "./config/filter.yaml"
required_fields = ["Element",
                   "Control System Name",
                   "Area",
                   "Keyword",
                   "Beampath",
                   "SumL (m)"]

with (open(csv_location, "r") as file_csv,
      open(filter_location, "r") as file_filter):
    # convert csv file into dictionary for filtering
    csv_reader = csv.DictReader(f=file_csv)
    filter_dict = yaml.safe_load(file_filter)

    # make the elements from csv stripped out with only information we need
    def _is_required_field(pair: tuple):
        key, value = pair
        required = key in required_fields
        caught = False
        if key in filter_dict:
            for f in filter_dict[key]:
                caught = caught or value.startswith(f)
        return required and not caught

    # only store the required fields from lcls_elements, there are lots more!
    elements = [
        dict(filter(_is_required_field, element.items()))
        for element in csv_reader
    ]

for e in elements:
    if "Area" in e:
        if e["Area"] == "\t- NO AREA -":
            print("'" + e["Area"] + "'")
