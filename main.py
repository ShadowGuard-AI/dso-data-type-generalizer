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
        pd.DataFrame: The DataFrame with generalized data types.
    Raises:
        ValueError: If an invalid type is specified in the type map or if a conversion fails.
    """

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

    for col in df.columns:
        col_type = df[col].dtype

        # Correctly handle 'object' dtype, which can represent strings or mixed data types
        if col_type == 'object':
          # Check if all values are strings. If so, treat as 'str'
          try:
              df[col] = df[col].astype(str)
              col_type_name = 'str'
          except:
              col_type_name = 'object' #leave it alone.



        elif pd.api.types.is_integer_dtype(df[col]):
            col_type_name = 'int'
        elif pd.api.types.is_float_dtype(df[col]):
            col_type_name = 'float'
        elif pd.api.types.is_bool_dtype(df[col]):
            col_type_name = 'bool'
        else:
            col_type_name = 'object'  # Handles mixed data types or other cases

        if col_type_name in type_map:
            new_type = type_map[col_type_name]

            try:
                if new_type == 'float':
                    df[col] = df[col].astype(float)
                elif new_type == 'str':
                    df[col] = df[col].astype(str)
                elif new_type == 'int':
                    df[col] = df[col].astype(int) #potential data loss, be careful!
                elif new_type == 'bool':
                    df[col] = df[col].astype(bool)
                elif new_type == 'object':
                    pass #already object do nothing.
                else:
                    logging.error(f"Invalid new type specified for conversion: {new_type}")
                    raise ValueError(f"Invalid new type: {new_type}")


                logging.info(f"Converted column '{col}' from {col_type_name} to {new_type}")

            except ValueError as e:
                logging.error(f"Failed to convert column '{col}' from {col_type_name} to {new_type}: {e}")
                raise ValueError(f"Failed to convert column '{col}' from {col_type_name} to {new_type}: {e}")


    return df


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

    try:
        # Load data securely.  Explicitly specifying encoding is important.  UTF-8 is a generally safe default.
        # Can be expanded upon to auto-detect and handle more encodings securely.
        df = pd.read_csv(input_file, encoding='utf-8')  #  Explicitly define encoding

        # Generalize data types
        df = generalize_data_type(df, type_map_str)

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