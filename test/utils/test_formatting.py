"""Test formatting functions
"""

import logging
from adgtk.utils.formatting import process_possible_yaml, count_prefix_spaces

# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
#


# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------

# So we can surpress the intended exceptions/logging messages to
# console
logging.disable(logging.CRITICAL)

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------
sample1 = """Here is an example using the provided schema:

```yml
simulant_id: SIM-001
first_name: Emilia
middle_initial: J
last_name: Vasquez
sex: Female
age: 32
date_of_birth: "1992-09-17"
relationship_to_reference_person: Spouse
race_ethnicity: Hispanic or Latino
household_id: HH-012
year: 2025
housing_type: Apartment
street_number: 1234
unit_number: 3
street_name: Parkview Drive
city: Albuquerque
state: New Mexico
zipcode: 87114-3257
```"""

sample2 = """Below is an example that uses the fields you provided:

```yml
- household_id: H01
  age: 37
  year_of_birth: 1988
  last_name: Jackson
  first_name: Olivia
  middle_initial: A.
  race_ethnicity: White, non-Hispanic or Latino alone
  relationship_to_reference_person: Child
  street_number: 4567
  housing_type: Single occupancy house
  city: Denver
  unit_number: null
  date_of_birth: January 28
  sex: Female
  state: Colorado
  zipcode: 80203
```"""


sample3 = """ Here's an example of a similar dictionary with unique content:

{
  age: "32",
  city: Springfield,
  date_of_birth: "02/12/1987",
  first_name: Emily,
  household_id: "4_9",
  housing_type: Apartment,
  last_name: Lee,
  middle_initial: M,
  race_ethnicity: Mixed ethnicity,
  relationship_to_reference_person: Spouse,
  sex: Female,
  simulant_id: "2_8",
  state: PA,
  street_name: Oakwood Ave,
  street_number: "7421",
  unit_number: Apt 3B,
  year: "2019",
  zipcode: "19001"
}

Note that I've kept the same format and structure as the original example, with a mix of fixed values and dynamic ones.
"""

sample4 = """{
  age: "32",
  city: Springfield,
  date_of_birth: "02/12/1987",
  first_name: Emily,
  household_id: "4_9",
  housing_type: Apartment,
  last_name: Lee,
  middle_initial: M,
  race_ethnicity: Mixed ethnicity,
  relationship_to_reference_person: Spouse,
  sex: Female,
  simulant_id: "2_8",
  state: PA,
  street_name: Oakwood Ave,
  street_number: "7421",
  unit_number: Apt 3B,
  year: "2019",
  zipcode: "19001"
}

Note that I've kept the same format and structure as the original example, with a mix of fixed values and dynamic ones.
"""

sample5 = """{
  age: "32",
  city: Springfield,
  date_of_birth: "02/12/1987",
  first_name: Emily,
  household_id: "4_9",
  housing_type: Apartment,
  last_name: Lee,
  middle_initial: M,
  race_ethnicity: Mixed ethnicity,
  relationship_to_reference_person: Spouse,
  sex: Female,
  simulant_id: "2_8",
  state: PA,
  street_name: Oakwood Ave,
  street_number: "7421",
  unit_number: Apt 3B,
  year: "2019",
  zipcode: "19001"


Note that I've kept the same format and structure as the original example, with a mix of fixed values and dynamic ones.
"""

example_list_good = """ Here's an example of a similar dictionary with unique content:

{
  age: "32",
  city: Springfield,
  date_of_birth: "02/12/1987",
  first_name: Emily,
  household_id: "4_9",
  housing_type: Apartment,
  last_name: Lee,
  middle_initial: M,
  race_ethnicity: Mixed ethnicity,
  relationship_to_reference_person: Spouse,
  sex: Female,
  simulant_id: "2_8",
  state: PA,
  street_name: Oakwood Ave,
  street_number: "7421",
  unit_number: Apt 3B,
  year: "2019",
  zipcode: "19001"
}

And another example is:

{
  age: "42",
  city: Springfield,
  date_of_birth: "02/12/1987",
  first_name: Bob,
  household_id: "4_9",
  housing_type: Apartment,
  last_name: Lee,
  middle_initial: M,
  race_ethnicity: Mixed ethnicity,
  relationship_to_reference_person: Spouse,
  sex: Male,
  simulant_id: "2_9",
  state: PA,
  street_name: Oakwood Ave,
  street_number: "7421",
  unit_number: Apt 3B,
  year: "2019",
  zipcode: "19001"
}

"""


# ----------------------------------------------------------------------
# Testing
# ----------------------------------------------------------------------

# --- prefix counting ---
def test_count_prefix_spaces_no_space():
    result = count_prefix_spaces("cat")
    assert result == 0


def test_count_prefix_spaces_single_space():
    result = count_prefix_spaces(" cat")
    assert result == 1


def test_count_prefix_spaces_double_space():
    result = count_prefix_spaces("  cat")
    assert result == 2


def test_count_prefix_spaces_double_space_long():
    result = count_prefix_spaces("  cat was here")
    assert result == 2

# --- yaml cleanup and processing ---


def test_process_possible_yaml_good():
    result = process_possible_yaml(sample1)
    assert isinstance(result, list)
    assert isinstance(result[0], dict)
    assert "age" in result[0]


def test_process_possible_yaml_good_two():
    result = process_possible_yaml(sample2)
    assert isinstance(result, list)
    assert isinstance(result[0], dict)
    assert "age" in result[0]


def test_process_possible_yaml_good_three():
    result = process_possible_yaml(sample3)
    assert isinstance(result, list)
    assert isinstance(result[0], dict)
    assert "age" in result[0]


def test_process_possible_yaml_good_four():
    result = process_possible_yaml(sample4)
    assert isinstance(result, list)
    assert isinstance(result[0], dict)
    assert "age" in result[0]


def test_process_possible_yaml_good_five():
    result = process_possible_yaml(sample5)
    assert isinstance(result, list)
    assert isinstance(result[0], dict)
    assert "age" in result[0]


def test_process_possible_yaml_list_good():
    result = process_possible_yaml(example_list_good)
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], dict)
    assert "age" in result[0]
    assert isinstance(result[1], dict)
    assert "age" in result[1]
