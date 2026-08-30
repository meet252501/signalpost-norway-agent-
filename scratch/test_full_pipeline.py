from src.budget import BatchBudget
from src.pipeline import process_company


def main():
    budget = BatchBudget()
    print("Running pipeline on real company: EQUINOR ASA (923609016)...")
    result = process_company("923609016", budget)
    print("\nResult:")
    print(result.model_dump_json(indent=2))
    print("\nBudget summary:")
    print(budget.summary())


if __name__ == "__main__":
    main()
