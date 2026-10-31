![Banner](banner.png)

# dso-data-type-generalizer
Replaces specific data types with more general ones (e.g., converts all integers to floats within a dataset).  Useful to introduce a layer of fuzziness without drastically altering the dataset's usability for some downstream purposes. Requires the pandas library. - Focused on Tools for sanitizing and obfuscating sensitive data within text files and structured data formats

## Install
`git clone https://github.com/ShadowGuardAI/dso-data-type-generalizer`

## Usage
`./dso-data-type-generalizer [params]`

## Parameters
- `-h`: Show help message and exit
- `--type_map`: A string defining type conversions in the form of

## Behavior
- An output path that resolves to the input file is refused at exit 1, however it is spelled.
- A run where no column matched the type map, or the input has no data rows, exits non-zero with no success line and writes no output.
- The object target converts a column to object dtype for real, and the conversion is logged only when the dtype actually changes.

## License
Copyright (c) ShadowGuardAI
