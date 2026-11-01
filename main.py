import argparse
import logging
import pandas as pd
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.
    Returns:
        argparse.ArgumentParser: The configured argument parser.
    """
    parser = argparse.ArgumentParser(description="Generalizes data types in a CSV file (e.g., integers to floats).")

    parser.add_argument("input_file", help="Path to the input CSV file.")
    parser.add_argument("output_file", help="Path to the output CSV file.")
    parser.add_argument("--type_map", help="A string defining type conversions in the form of 'old_type:new_type[,old_type:new_type,...]'. "
                                       "Examples: 'int:float', 'int:float,bool:str'. Supported types: int, float, str, bool, object.",
                        required=True)

    return parser


def generalize_data_type(df, type_map_str):
    """
    Generalizes data types in a Pandas DataFrame based on the provided type map.
    Args:
        df (pd.DataFrame): The input DataFrame.
        type_map_str (str): A string defining type conversions (e.g., 'int:float,bool:str').
    Returns:
        tuple: The DataFrame with generalized data types, and the number
        of columns whose classified type matched the type map.
    Raises:
        ValueError: If an invalid type is specified in the type map or if a conversion fails.
    """

    # The map is keyed by type class, never by column name, so one entry
    # converts every column in the file that classifies to that type.
    # Naming the same old type twice is not an error: the later entry
    # silently replaces the earlier one in this dict.
    type_map = {}
    try:
        for conversion in type_map_str.split(','):
            old_type, new_type = conversion.split(':')
            old_type = old_type.strip().lower()
            new_type = new_type.strip().lower()

            if old_type not in ['int', 'float', 'str', 'bool', 'object']:
                raise ValueError(f"Invalid old type: {old_type}. Supported types are: int, float, str, bool, object.")
            if new_type not in ['int', 'float', 'str', 'bool', 'object']:
                raise ValueError(f"Invalid new type: {new_type}. Supported types are: int, float, str, bool, object.")

            type_map[old_type] = new_type

    except ValueError as e:
        logging.error(f"Error parsing type map: {e}")
        raise

    matched_columns = 0

    for col in df.columns:
        col_type = df[col].dtype

        # Classification only reads the column; it must not rewrite it.
        # The old object branch converted the column to str while deciding
        # what it was, changing columns the type map never asked to touch.
        if pd.api.types.is_string_dtype(df[col]):
            # Current pandas reads text columns with a dedicated string
            # dtype rather than object. Without this check those columns
            # fell through to 'object' and a 'str' mapping never fired.
            col_type_name = 'str'
        elif col_type == 'object':
            # A true object column is 'str' only if every present value is
            # one; anything mixed stays 'object'.
            present = df[col].dropna()
            col_type_name = 'str' if len(present) and present.map(lambda v: isinstance(v, str)).all() else 'object'
        elif pd.api.types.is_integer_dtype(df[col]):
            col_type_name = 'int'
        elif pd.api.types.is_float_dtype(df[col]):
            col_type_name = 'float'
        elif pd.api.types.is_bool_dtype(df[col]):
            col_type_name = 'bool'
        else:
            col_type_name = 'object'  # Handles mixed data types or other cases

        if col_type_name in type_map:
            # The match is counted before the conversion runs, and main
            # reads this count as proof something changed. An object
            # target on a column already stored as object sets converted
            # to False below, logs nothing, and still counts here, so a
            # run can pass the count check with a column whose dtype
            # never moved. The conversions themselves follow astype
            # rules, which are worth knowing per target: float to int
            # truncates toward zero (2.9 and -2.9 become 2 and -2, which
            # I verified), and anything to bool reads every nonzero
            # number and every non-empty string as True, including the
            # string False if a column reaches this branch as text.
            matched_columns += 1
            new_type = type_map[col_type_name]

            try:
                converted = True
                if new_type == 'float':
                    df[col] = df[col].astype(float)
                elif new_type == 'str':
                    df[col] = df[col].astype(str)
                elif new_type == 'int':
                    df[col] = df[col].astype(int) #potential data loss, be careful!
                elif new_type == 'bool':
                    df[col] = df[col].astype(bool)
                elif new_type == 'object':
                    # Convert for real: the old branch was a pass that
                    # still logged a conversion. Log only when the dtype
                    # actually changes to object.
                    before_dtype = df[col].dtype
                    df[col] = df[col].astype(object)
                    converted = df[col].dtype != before_dtype
                else:
                    logging.error(f"Invalid new type specified for conversion: {new_type}")
                    raise ValueError(f"Invalid new type: {new_type}")


                if converted:
                    logging.info(f"Converted column '{col}' from {col_type_name} to {new_type}")

            except ValueError as e:
                logging.error(f"Failed to convert column '{col}' from {col_type_name} to {new_type}: {e}")
                raise ValueError(f"Failed to convert column '{col}' from {col_type_name} to {new_type}: {e}")


    return df, matched_columns


def main():
    """
    Main function to execute the data type generalization.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    input_file = args.input_file
    output_file = args.output_file
    type_map_str = args.type_map

    # Input validation
    if not os.path.exists(input_file):
        logging.error(f"Input file not found: {input_file}")
        sys.exit(1)

    # Refuse in place output: an output path that resolves to the input
    # file (same spelling, ./ alias, or symlink) would destroy the
    # original before anyone can compare the two.
    if os.path.realpath(output_file) == os.path.realpath(input_file):
        logging.error("Output file resolves to the input file; refusing to overwrite it in place.")
        sys.exit(1)

    try:
        # Load data securely.  Explicitly specifying encoding is important.  UTF-8 is a generally safe default.
        # Can be expanded upon to auto-detect and handle more encodings securely.
        df = pd.read_csv(input_file, encoding='utf-8')  #  Explicitly define encoding

        # A header with no data rows holds nothing to generalize, so it
        # fails instead of writing an empty result under a success line.
        if len(df) == 0:
            logging.error("Input file has no data rows: nothing to generalize.")
            sys.exit(1)

        # Generalize data types
        df, matched_columns = generalize_data_type(df, type_map_str)

        # A type map that matched no column changed nothing, so it fails
        # instead of writing identical output under a success line.
        if matched_columns == 0:
            logging.error("No column matched the type map: nothing was generalized.")
            sys.exit(1)

        # Save the modified DataFrame
        df.to_csv(output_file, index=False, encoding='utf-8')
        logging.info(f"Successfully generalized data types and saved to {output_file}")

    except FileNotFoundError:
        logging.error(f"File not found: {input_file}")
        sys.exit(1)
    except ValueError as e:
        logging.error(f"ValueError: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        logging.exception(e) # Log the traceback for debugging
        sys.exit(1)



if __name__ == "__main__":
    # Example usage (can be put into a docstring or separate file):
    # python main.py input.csv output.csv --type_map "int:float"
    # python main.py input.csv output.csv --type_map "int:str,bool:float"
    # python main.py input.csv output.csv --type_map "int:float,str:object"
    main()