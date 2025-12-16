import pandas as pd
import os
import sys

def get_csv_files():
    """Lists all CSV files in the current directory."""
    csv_files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]
    return csv_files

def select_csv_file(csv_files):
    """Allows the user to select a CSV file from a list."""
    if not csv_files:
        print("No CSV files found in the current directory.")
        sys.exit()

    print("\nAvailable CSV files:")
    for i, file_name in enumerate(csv_files):
        print(f"{i + 1}. {file_name}")

    while True:
        try:
            choice = input("Enter the number of the CSV file to clean: ")
            index = int(choice) - 1
            if 0 <= index < len(csv_files):
                return csv_files[index]
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def get_columns_to_remove(df_columns):
    """Prompts the user to enter column numbers to remove and converts them to names."""
    print("\nColumns in the selected CSV file:")
    for i, col_name in enumerate(df_columns.tolist()):
        print(f"{i + 1} - {col_name}")

    while True:
        columns_input = input(
            "\nEnter the column NUMBERS to remove (comma-separated), or type 'list' to see columns again: "
        ).strip()

        if columns_input.lower() == 'list':
            print("\nColumns in the selected CSV file:")
            for i, col_name in enumerate(df_columns.tolist()):
                print(f"{i + 1} - {col_name}")
            continue

        if not columns_input:
            print("No column numbers entered. Please enter numbers or 'list'.")
            continue

        # Process the input numbers
        selected_indices = []
        invalid_inputs = []
        col_names_to_remove = []

        raw_numbers = [num.strip() for num in columns_input.split(',')]

        for num_str in raw_numbers:
            try:
                col_index = int(num_str) - 1 # Convert to 0-based index
                if 0 <= col_index < len(df_columns):
                    selected_indices.append(col_index)
                else:
                    invalid_inputs.append(num_str)
            except ValueError:
                invalid_inputs.append(num_str)

        if invalid_inputs:
            print(f"Warning: The following inputs were invalid (not numbers or out of range): {', '.join(invalid_inputs)}")
            print("Please re-enter valid column numbers.")
            continue # Ask for input again

        if not selected_indices:
            print("No valid column numbers selected. Please try again.")
            continue

        # Convert valid indices to column names
        for index in selected_indices:
            col_names_to_remove.append(df_columns[index])

        # Remove duplicates while preserving order for consistency
        col_names_to_remove = list(dict.fromkeys(col_names_to_remove))

        return col_names_to_remove

def confirm_changes(original_columns, columns_to_remove):
    """Presents a summary of changes and asks for user confirmation."""
    df_columns_list = original_columns.tolist()
    # Ensure columns_to_remove only contains actual existing columns
    valid_cols_to_remove = [col for col in columns_to_remove if col in df_columns_list]
    invalid_cols_entered = [col for col in columns_to_remove if col not in df_columns_list]

    # Calculate remaining columns
    remaining_columns = [col for col in df_columns_list if col not in valid_cols_to_remove]

    print("\n--- Proposed Changes Summary ---")

    print(f"**Original Columns ({len(original_columns)}):**")
    if original_columns.empty:
        print("  (No columns found)")
    else:
        for col in df_columns_list:
            print(f"  - {col}")

    print(f"\n**Columns to be REMOVED ({len(valid_cols_to_remove)}):**")
    if not valid_cols_to_remove:
        print("  (None selected for removal or no valid columns found for removal)")
    else:
        for col in valid_cols_to_remove:
            print(f"  - {col}")

    if invalid_cols_entered:
        print(f"\n**WARNING: The following columns were entered (by number) but NOT found in the CSV:**")
        for col in invalid_cols_entered:
            print(f"  - {col}")

    print(f"\n**Columns that will REMAIN ({len(remaining_columns)}):**")
    if not remaining_columns:
        print("  (No columns will remain after removal)")
    else:
        for col in remaining_columns:
            print(f"  - {col}")
    print("------------------------------")

    while True:
        action = input(
            "Confirm changes? (yes/no/update): "
        ).strip().lower()
        if action in ['yes', 'y']:
            return 'confirm'
        elif action in ['no', 'n']:
            return 'decline'
        elif action in ['update', 'u']:
            return 'update'
        else:
            print("Invalid input. Please type 'yes', 'no', or 'update'.")

def main():
    print("CSV Cleanup Script")
    print("------------------")

    # Step 1: List CSV files
    csv_files = get_csv_files()
    if not csv_files:
        print("No CSV files found in the current directory. Please place CSV files here.")
        sys.exit()

    # Step 2: User selects CSV
    selected_file = select_csv_file(csv_files)
    print(f"\nLoading '{selected_file}'...")

    try:
        df = pd.read_csv(selected_file)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit()

    original_columns = df.columns

    while True:
        # Step 3 & 4: Get columns to remove (now by number)
        columns_to_remove = get_columns_to_remove(original_columns)

        # Step 5: Summary and Confirmation Loop
        action = confirm_changes(original_columns, columns_to_remove)

        if action == 'confirm':
            break  # Exit the loop and proceed to clean
        elif action == 'decline':
            print("Operation cancelled. Exiting.")
            sys.exit()
        elif action == 'update':
            print("Updating column selection...\n")
            continue # Go back to column selection

    # Identify actual columns to drop (already done by get_columns_to_remove logic)
    cols_to_drop_actual = [col for col in columns_to_remove if col in original_columns]

    if not cols_to_drop_actual:
        print("No valid columns selected for removal. No changes will be made.")
        sys.exit()

    # Step 6: Create cleaned CSV
    print(f"\nDropping columns: {', '.join(cols_to_drop_actual)}")
    cleaned_df = df.drop(columns=cols_to_drop_actual, inplace=False)

    # Construct output filename
    base_name, ext = os.path.splitext(selected_file)
    output_filename = f"{base_name}_cleaned{ext}"

    try:
        cleaned_df.to_csv(output_filename, index=False)
        print(f"\nSuccessfully cleaned CSV and saved to '{output_filename}'")
    except Exception as e:
        print(f"Error saving cleaned CSV: {e}")
        sys.exit()

if __name__ == "__main__":
    main()